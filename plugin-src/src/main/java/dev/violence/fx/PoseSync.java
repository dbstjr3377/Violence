package dev.violence.fx;

import dev.violence.ViolencePlugin;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import java.util.logging.Level;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;

/**
 * 3인칭 한 팔 조준 자세.
 * 바닐라에서 한 팔만 들어 겨누는 자세는 "뿔 불기 동작의 아이템을 사용 중"일 때만 나온다.
 * 그래서 보는 사람에게만 "이 개체가 손에 든 아이템을 사용 중" 이라는 엔티티 상태(살아있는 개체 플래그)를 보낸다.
 * 본인 클라이언트에는 보내지 않으므로 이동 속도 등에 영향이 없다.
 * 패킷 생성에 실패하면 기능만 꺼진다 (기본 들기 자세로 보임).
 */
public final class PoseSync {
    private final ViolencePlugin plugin;
    private boolean ok;
    private Object flagsAccessor;
    private Method createValue;
    private Constructor<?> packetCtor;
    private Method getHandle;
    private Field connectionField;
    private Method sendMethod;

    public PoseSync(ViolencePlugin plugin) {
        this.plugin = plugin;
        try {
            Class<?> living = Class.forName("net.minecraft.world.entity.LivingEntity");
            Field f = living.getDeclaredField("DATA_LIVING_ENTITY_FLAGS");
            f.setAccessible(true);
            flagsAccessor = f.get(null);
            Class<?> accessorClass = Class.forName("net.minecraft.network.syncher.EntityDataAccessor");
            Class<?> dataValue = Class.forName("net.minecraft.network.syncher.SynchedEntityData$DataValue");
            createValue = dataValue.getMethod("create", accessorClass, Object.class);
            Class<?> pkt = Class.forName("net.minecraft.network.protocol.game.ClientboundSetEntityDataPacket");
            packetCtor = pkt.getConstructor(int.class, List.class);
            Class<?> packetIface = Class.forName("net.minecraft.network.protocol.Packet");
            Class<?> craftPlayer = Class.forName(plugin.getServer().getClass().getPackageName() + ".entity.CraftPlayer");
            getHandle = craftPlayer.getMethod("getHandle");
            connectionField = Class.forName("net.minecraft.server.level.ServerPlayer").getField("connection");
            for (Method m : connectionField.getType().getMethods()) {
                if (m.getName().equals("send") && m.getParameterCount() == 1 && m.getParameterTypes()[0].isAssignableFrom(packetIface)) {
                    sendMethod = m;
                    break;
                }
            }
            ok = sendMethod != null;
        } catch (Throwable t) {
            plugin.getLogger().log(Level.WARNING, "한 팔 조준 자세 초기화 실패 - 기본 들기 자세로 보입니다: " + t);
            ok = false;
        }
    }

    /** viewer 에게 target 이 주 손 아이템을 사용 중(true)/아님(false) 으로 보이게 한다. */
    public void sendUsing(Player viewer, LivingEntity target, boolean using) {
        if (!ok || viewer.equals(target)) return;
        try {
            Object value = createValue.invoke(null, flagsAccessor, (byte) (using ? 1 : 0));
            Object packet = packetCtor.newInstance(target.getEntityId(), List.of(value));
            Object conn = connectionField.get(getHandle.invoke(viewer));
            sendMethod.invoke(conn, packet);
        } catch (Throwable t) {
            plugin.getLogger().log(Level.WARNING, "한 팔 조준 자세 패킷 실패 - 기능을 끕니다: " + t);
            ok = false;
        }
    }
}
