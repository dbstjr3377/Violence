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
 * 3인칭 자세 동기화 (보는 사람에게만 보내는 엔티티 상태).
 * - 한 팔 조준 / 두 손 근접 대기: "주 손 아이템 사용 중" 플래그
 * - 근접 좌우 대기: 주 손(왼손/오른손) 값. 왼손 주 손이면 바닐라가 팔 자세와 휘두르기를 좌우로 뒤집는다
 *
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
    /** 개체 종류별 주 손 데이터 (없으면 null) */
    private final java.util.Map<Class<?>, Object[]> mainHand = new java.util.HashMap<>();
    private final java.util.Map<Class<?>, Method> handles = new java.util.HashMap<>();
    private boolean mainHandOk = true;

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

    /**
     * viewer 에게 target 이 "방금 주 손 아이템을 쓰기 시작한" 것으로 보이게 한다 (사용 시간 0 부터 다시).
     * 근접 3인칭 휘두르기 프레임(사용 시간 기준)을 처음부터 재생할 때 쓴다.
     */
    public void restartUsing(Player viewer, LivingEntity target) {
        sendUsing(viewer, target, false);
        sendUsing(viewer, target, true);
    }

    /** viewer 에게 target 의 주 손을 왼손(true)/오른손(false) 으로 보이게 한다. 지원하지 않는 개체는 무시. */
    public void sendMainHand(Player viewer, LivingEntity target, boolean left) {
        if (!ok || !mainHandOk || viewer.equals(target)) return;
        try {
            Method h = handles.get(target.getClass());
            if (h == null) {
                h = target.getClass().getMethod("getHandle");
                handles.put(target.getClass(), h);
            }
            Object handle = h.invoke(target);
            Object[] acc = mainHand.computeIfAbsent(handle.getClass(), c -> findMainHand(handle));
            if (acc == null) return;
            Object v;
            if (acc[1] instanceof Class<?> cls && cls.isEnum()) v = enumValue(cls, left ? "LEFT" : "RIGHT");
            else v = (byte) (left ? 0 : 1);
            Object value = createValue.invoke(null, acc[0], v);
            Object packet = packetCtor.newInstance(target.getEntityId(), List.of(value));
            Object conn = connectionField.get(getHandle.invoke(viewer));
            sendMethod.invoke(conn, packet);
        } catch (Throwable t) {
            plugin.getLogger().log(Level.WARNING, "주 손 자세 패킷 실패 - 근접 좌우 대기를 끕니다: " + t);
            mainHandOk = false;
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Object enumValue(Class<?> cls, String name) {
        return Enum.valueOf((Class) cls, name);
    }

    /** {접근자, 값 종류} — 클래스 계층에서 DATA_PLAYER_MAIN_HAND 를 찾고, 현재 값으로 종류(열거형/바이트)를 정한다 */
    private Object[] findMainHand(Object handle) {
        for (Class<?> c = handle.getClass(); c != null; c = c.getSuperclass()) {
            Field f;
            try {
                f = c.getDeclaredField("DATA_PLAYER_MAIN_HAND");
            } catch (NoSuchFieldException e) {
                continue;
            }
            try {
                f.setAccessible(true);
                Object acc = f.get(null);
                Object data = handle.getClass().getMethod("getEntityData").invoke(handle);
                Method get = null;
                for (Method m : data.getClass().getMethods()) {
                    if (m.getName().equals("get") && m.getParameterCount() == 1) {
                        get = m;
                        break;
                    }
                }
                Object cur = get == null ? null : get.invoke(data, acc);
                Class<?> kind = cur == null ? Byte.class : (cur.getClass().isEnum() ? cur.getClass() : (cur.getClass().getSuperclass() != null && cur.getClass().getSuperclass().isEnum() ? cur.getClass().getSuperclass() : cur.getClass()));
                if (kind != Byte.class && !kind.isEnum()) return null;
                return new Object[] {acc, kind};
            } catch (ReflectiveOperationException | RuntimeException e) {
                plugin.getLogger().log(Level.WARNING, "주 손 데이터 찾기 실패 - 근접 좌우 대기를 끕니다: " + e);
                return null;
            }
        }
        return null;
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
