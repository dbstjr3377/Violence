package dev.violence.fx;

import dev.violence.ViolencePlugin;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Level;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;

/**
 * 시점 전환 (처형/사망 연출).
 * 카메라 패킷(ClientboundSetCameraPacket)을 직접 보내서 플레이어는 생존 모드를 유지한 채
 * 다른 엔티티의 시점으로 화면만 옮긴다. 클라이언트의 1/3인칭 설정은 그대로 남으므로
 * 카메라를 되돌리면 자동으로 사용자 설정 시점으로 복귀한다.
 * 패킷 전송이 실패하면 관전 모드 방식으로 대체한다.
 */
public final class CameraService {
    private final ViolencePlugin plugin;
    private boolean reflectionOk;
    private Method getHandle;
    private Field connectionField;
    private Method sendMethod;
    private Constructor<?> cameraPacketCtor;
    private final Map<UUID, ItemDisplay> cameras = new HashMap<>();
    private final Map<UUID, GameMode> fallbackModes = new HashMap<>();
    private final Map<UUID, Location> fallbackLocations = new HashMap<>();

    public CameraService(ViolencePlugin plugin) {
        this.plugin = plugin;
        try {
            Class<?> nmsEntity = Class.forName("net.minecraft.world.entity.Entity");
            Class<?> packetClass = Class.forName("net.minecraft.network.protocol.game.ClientboundSetCameraPacket");
            Class<?> packetIface = Class.forName("net.minecraft.network.protocol.Packet");
            cameraPacketCtor = packetClass.getConstructor(nmsEntity);
            Class<?> craftPlayer = Class.forName(plugin.getServer().getClass().getPackageName() + ".entity.CraftPlayer");
            getHandle = craftPlayer.getMethod("getHandle");
            Class<?> serverPlayer = Class.forName("net.minecraft.server.level.ServerPlayer");
            connectionField = serverPlayer.getField("connection");
            Class<?> connClass = connectionField.getType();
            for (Method m : connClass.getMethods()) {
                if (m.getName().equals("send") && m.getParameterCount() == 1 && m.getParameterTypes()[0].isAssignableFrom(packetIface)) {
                    sendMethod = m;
                    break;
                }
            }
            reflectionOk = sendMethod != null;
        } catch (Throwable t) {
            plugin.getLogger().log(Level.WARNING, "카메라 패킷 초기화 실패 - 관전 모드 방식으로 대체합니다: " + t);
            reflectionOk = false;
        }
    }

    private Object handle(Entity e) throws Exception {
        Method m = e.getClass().getMethod("getHandle");
        return m.invoke(e);
    }

    private boolean sendCamera(Player p, Entity target) {
        if (!reflectionOk) return false;
        try {
            Object packet = cameraPacketCtor.newInstance(handle(target));
            Object sp = getHandle.invoke(p);
            Object conn = connectionField.get(sp);
            sendMethod.invoke(conn, packet);
            return true;
        } catch (Throwable t) {
            plugin.getLogger().log(Level.WARNING, "카메라 패킷 전송 실패: " + t);
            reflectionOk = false;
            return false;
        }
    }

    /** 카메라 엔티티를 만든다 (보이지 않는 아이템 디스플레이). */
    public ItemDisplay spawnCamera(Location at, int smoothTicks) {
        ItemDisplay cam = at.getWorld().spawn(at, ItemDisplay.class, d -> {
            d.setPersistent(false);
            d.setTeleportDuration(smoothTicks);
            d.setViewRange(8f);
        });
        if (plugin.arena() != null) plugin.arena().track(cam);
        return cam;
    }

    /** 플레이어의 화면을 cam 엔티티 시점으로 전환. */
    public void view(Player p, ItemDisplay cam) {
        ItemDisplay old = cameras.put(p.getUniqueId(), cam);
        if (old != null && old != cam && old.isValid()) old.remove();
        if (sendCamera(p, cam)) {
            hideHands(p);
            // 같은 틱에 바뀐 손 아이템 동기화가 뒤에 도착해도 다시 숨김
            plugin.later(1, () -> { if (p.isOnline() && cameras.get(p.getUniqueId()) == cam) hideHands(p); });
        } else {
            fallbackModes.putIfAbsent(p.getUniqueId(), p.getGameMode());
            fallbackLocations.putIfAbsent(p.getUniqueId(), p.getLocation());   // 관전하면 몸이 카메라로 따라가므로 원래 자리 기억
            p.setGameMode(GameMode.SPECTATOR);
            p.setSpectatorTarget(cam);
        }
    }

    /**
     * 카메라로 볼 때도 클라이언트는 자기 손(빈손이면 팔, 아니면 아이템)을 1인칭으로 그린다.
     * 자기 자신에게만 투명 아이템을 쥔 것처럼 보내서 숨김 (서버 인벤토리는 그대로, reset 에서 다시 동기화).
     */
    public void hideHands(Player p) {
        if (!isViewing(p) || fallbackModes.containsKey(p.getUniqueId())) return;
        Map<org.bukkit.inventory.EquipmentSlot, org.bukkit.inventory.ItemStack> eq = new java.util.EnumMap<>(org.bukkit.inventory.EquipmentSlot.class);
        eq.put(org.bukkit.inventory.EquipmentSlot.HAND, dev.violence.weapon.WeaponItems.hiddenHand());
        eq.put(org.bukkit.inventory.EquipmentSlot.OFF_HAND, new org.bukkit.inventory.ItemStack(org.bukkit.Material.AIR));
        p.sendEquipmentChange(p, eq);
    }

    private final java.util.Random rnd = new java.util.Random();
    private final Map<ItemDisplay, Long> shakeUntil = new HashMap<>();

    /**
     * 카메라 흔들림: ticks 동안 카메라 자리와 시선을 무작위로 흔들며 줄였다가 제자리로.
     * 회전만 바꾸면 클라이언트에 1.4° 단위로만 전해져 작은 흔들림이 사라지므로 위치(degrees × 0.035블록)도 함께 흔든다.
     * 이 카메라로 보는 모든 사람(처형자·피처형자)의 화면이 흔들린다.
     */
    public void shake(ItemDisplay cam, double degrees, int ticks) {
        if (cam == null || !cam.isValid()) return;
        Location base = cam.getLocation();
        Long prev = shakeUntil.get(cam);
        if (prev != null && prev >= plugin.now()) {
            float[] b = shakeBase.get(cam);
            if (b != null) base = new Location(base.getWorld(), b[2], b[3], b[4], b[0], b[1]);
        }
        long end = plugin.now() + ticks;
        shakeUntil.put(cam, end);
        shakeBase.put(cam, new float[] {base.getYaw(), base.getPitch(), (float) base.getX(), (float) base.getY(), (float) base.getZ()});
        cam.setTeleportDuration(1);
        final Location b0 = base.clone();
        for (int k = 0; k <= ticks; k++) {
            final int i = k;
            plugin.later(k, () -> {
                if (!cam.isValid() || shakeUntil.getOrDefault(cam, -1L) != end) return;
                if (i == ticks) {
                    cam.teleport(b0);
                    shakeUntil.remove(cam);
                    shakeBase.remove(cam);
                    return;
                }
                double amp = degrees * (1.0 - (double) i / ticks);
                double m = amp * 0.035;
                Location l = b0.clone().add((rnd.nextDouble() * 2 - 1) * m, (rnd.nextDouble() * 2 - 1) * m, (rnd.nextDouble() * 2 - 1) * m);
                l.setYaw((float) (b0.getYaw() + (rnd.nextDouble() * 2 - 1) * amp));
                l.setPitch((float) (b0.getPitch() + (rnd.nextDouble() * 2 - 1) * amp * 0.8));
                cam.teleport(l);
            });
        }
    }

    private final Map<ItemDisplay, float[]> shakeBase = new HashMap<>();

    public ItemDisplay cameraOf(Player p) {
        return cameras.get(p.getUniqueId());
    }

    /** 사용자 시점으로 복귀. */
    public void reset(Player p) {
        ItemDisplay cam = cameras.remove(p.getUniqueId());
        GameMode fb = fallbackModes.remove(p.getUniqueId());
        Location back = fallbackLocations.remove(p.getUniqueId());
        if (fb != null) {
            if (p.isOnline()) {
                p.setSpectatorTarget(null);
                p.setGameMode(fb);
                if (back != null && back.isWorldLoaded()) p.teleport(back);
            }
        } else {
            sendCamera(p, p);
            if (cam != null && p.isOnline()) p.updateInventory();   // 숨겼던 1인칭 손 아이템 복구
        }
        if (cam != null && cam.isValid()) {
            // 다른 플레이어가 같은 카메라를 보고 있지 않으면 제거
            if (!cameras.containsValue(cam)) cam.remove();
        }
    }

    public boolean isViewing(Player p) {
        return cameras.containsKey(p.getUniqueId());
    }

    public void resetAll() {
        for (UUID id : new java.util.ArrayList<>(cameras.keySet())) {
            Player p = plugin.getServer().getPlayer(id);
            if (p != null) reset(p);
        }
        cameras.clear();
    }
}
