package dev.violence.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import org.joml.Matrix3d;
import org.joml.Quaterniond;
import org.joml.Vector3d;

/**
 * 쓰러질 때 넘어지는 동작의 키프레임 계산 (fall.json, 순수 계산이라 서버 없이 테스트 가능).
 * 언제나 뒤로 넘어진다: 뒤로 넘어짐(BACK), 두 팔을 벌리고 날아감(BLAST, 샷건처럼 강한 공격),
 * 뒤쪽 벽에 부딪혀 기대 앉음(WALL, 기절). 벽에 기댄 채 죽으면 WALL_DEATH, 기절한 적을 처형하는 발차기는 KICK.
 *
 * 바닐라 플레이어 모델과 같은 크기의 6부위(머리·몸통·두 팔·두 다리)를 몸 기준 좌표(x=왼쪽, y=위, z=앞, 블록)에 놓는다.
 * 몸 전체는 발을 기준으로 pitch 만큼 앞으로 기울고 발은 feet 위치로 옮겨지며, 팔다리·머리는 관절에서 따로 돈다.
 * 마지막 프레임은 바닐라 엎드린(SWIMMING) 자세와 같아서, 끝나고 실제 몸으로 바꿔도 튀지 않는다.
 */
public final class FallPose {
    /** 플레이어 모델 1픽셀 (블록). 바닐라는 플레이어 모델을 0.9375배로 그린다 */
    public static final double PX = 0.9375 / 16.0;

    public enum Part {
        HEAD(0, 24, 0, 0, 4, 0, 8, 8, 8),
        BODY(0, 12, 0, 0, 6, 0, 8, 12, 4),
        ARM_R(-5, 22, 0, -1, -4, 0, 4, 12, 4),
        ARM_L(5, 22, 0, 1, -4, 0, 4, 12, 4),
        LEG_R(-1.9, 12, 0, 0, -6, 0, 4, 12, 4),
        LEG_L(1.9, 12, 0, 0, -6, 0, 4, 12, 4);

        /** 관절 위치 (서 있을 때, 픽셀) */
        public final Vector3d joint;
        /** 관절에서 부위 중심까지 (픽셀) */
        public final Vector3d offset;
        /** 크기 (픽셀) */
        public final Vector3d size;

        Part(double jx, double jy, double jz, double ox, double oy, double oz, double sx, double sy, double sz) {
            joint = new Vector3d(jx, jy, jz);
            offset = new Vector3d(ox, oy, oz);
            size = new Vector3d(sx, sy, sz);
        }
    }

    /** 한 부위의 놓임: 중심(블록, 발 기준 몸 좌표)과 회전 */
    public record Placement(Vector3d center, Quaterniond rotation) {}

    /** feet: 발 위치(몸 기준), travel: 시작 위치 → 끝 위치 비율 (없으면 1) */
    public record Frame(double pitch, double feetY, double feetZ, double travel, Map<Part, double[]> joints) {}

    /** 동작 이름 (fall.json "kinds") */
    public enum Kind {
        /** 뒤로 넘어짐 */
        BACK("back"),
        /** 샷건 등 강한 공격: 두 팔을 벌리고 뒤로 날아감 */
        BLAST("blast"),
        /** 넘어지다 뒤쪽 벽에 부딪혀 기대 앉음 (기절) */
        WALL("wall"),
        /** 벽에 기대 기절한 상태에서 죽음 */
        WALL_DEATH("wall_death"),
        /** 처형자 발차기 */
        KICK("kick");

        public final String key;

        Kind(String key) { this.key = key; }
    }

    /** 동작이 끝난 자세 */
    public enum End {
        /** 등으로 누움 (침대 없는 SLEEPING 마네킹) */
        FACE_UP,
        /** 벽에 기대 앉음 (탈것에 앉은 마네킹) */
        SIT,
        /** 서 있음 (실제 몸으로 돌아감) */
        STAND
    }

    /** fall.json 의 공통 값 */
    public record Config(double backLift, double seatY, double seatAttach, double wallGap, double sitHeadPitch) {
        public static final Config DEFAULT = new Config(0.14, -0.5, 0.6, 0.25, 40);
    }

    private final List<Frame> frames;
    private final int holdTicks;
    private final End end;
    private final Config config;
    private final double slide;
    private final int contact;

    public FallPose(List<Frame> frames, int holdTicks) {
        this(frames, holdTicks, End.FACE_UP, Config.DEFAULT, 0, -1);
    }

    public FallPose(List<Frame> frames, int holdTicks, End end, Config config, double slide, int contact) {
        if (frames.isEmpty()) throw new IllegalArgumentException("프레임이 없습니다");
        this.frames = List.copyOf(frames);
        this.holdTicks = Math.max(frames.size(), holdTicks);
        this.end = end;
        this.config = config;
        this.slide = slide;
        this.contact = contact;
    }

    /** 모든 동작 */
    public static Map<Kind, FallPose> loadAll() {
        try (InputStream in = FallPose.class.getResourceAsStream("/fall.json")) {
            if (in == null) throw new IllegalStateException("fall.json 없음");
            JsonObject root = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
            Config cfg = new Config(num(root, "back_lift", 0.14), num(root, "seat_y", -0.5), num(root, "seat_attach", 0.6),
                    num(root, "wall_gap", 0.25), num(root, "sit_head_pitch", 40));
            JsonObject kinds = root.getAsJsonObject("kinds");
            Map<Kind, FallPose> out = new EnumMap<>(Kind.class);
            for (Kind k : Kind.values()) {
                JsonObject o = kinds.getAsJsonObject(k.key);
                FallPose p = parse(o);
                End end = switch (o.get("end").getAsString()) {
                    case "sit" -> End.SIT;
                    case "stand" -> End.STAND;
                    default -> End.FACE_UP;
                };
                out.put(k, new FallPose(p.frames, p.holdTicks, end, cfg, num(o, "slide", 0), (int) num(o, "contact", -1)));
            }
            return out;
        } catch (java.io.IOException e) {
            throw new IllegalStateException("fall.json 읽기 실패", e);
        }
    }

    private static double num(JsonObject o, String key, double def) {
        return o.has(key) ? o.get(key).getAsDouble() : def;
    }

    public End end() { return end; }

    public boolean faceUp() { return end == End.FACE_UP; }

    public Config config() { return config; }

    /** 누운 마네킹을 띄우는 높이 (바닥에 머리가 묻히지 않게) */
    public double lift() { return config.backLift(); }

    /** 시체가 밀려나는 거리 (살아 있으면 실제 몸이 밀려나므로 쓰지 않음) */
    public double slide() { return slide; }

    /** 발차기가 닿는 프레임 (없으면 -1) */
    public int contact() { return contact; }

    /** 마지막 프레임의 발 앞 거리 (누운 마네킹을 놓을 자리) */
    public double endForward() { return frames.get(frames.size() - 1).feetZ(); }

    /**
     * 넘어지는 방식: 방향과 상관없이 언제나 뒤로 넘어진다 (몸은 맞은 쪽을 향해 돌아감).
     * 뒤쪽에 벽이 있으면 벽에 기대 앉고, 강한 공격이면 팔을 벌리고 날아간다.
     */
    public static Kind kindFor(boolean strong, boolean wallBehind) {
        if (wallBehind) return Kind.WALL;
        return strong ? Kind.BLAST : Kind.BACK;
    }

    /** 넘어지는 동안 몸 방향: 처음 3프레임에 걸쳐 원래 방향에서 맞은 쪽을 보는 방향으로 돌아감 */
    public static float spinYaw(float from, float to, int frame) {
        double t = Math.min(1.0, frame / 3.0);
        t = t * t * (3 - 2 * t);
        double d = ((to - from) % 360 + 540) % 360 - 180;
        return (float) (from + d * t);
    }

    public static FallPose parse(JsonObject root) {
        List<Frame> list = new ArrayList<>();
        for (JsonElement el : root.getAsJsonArray("frames")) {
            JsonObject o = el.getAsJsonObject();
            JsonArray feet = o.getAsJsonArray("feet");
            Map<Part, double[]> joints = new EnumMap<>(Part.class);
            for (Part p : Part.values()) {
                String key = p.name().toLowerCase(java.util.Locale.ROOT);
                if (!o.has(key)) continue;
                JsonArray a = o.getAsJsonArray(key);
                joints.put(p, new double[] {a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()});
            }
            list.add(new Frame(o.get("pitch").getAsDouble(), feet.get(0).getAsDouble(), feet.get(1).getAsDouble(),
                    num(o, "travel", 1.0), joints));
        }
        int hold = root.has("hold_ticks") ? root.get("hold_ticks").getAsInt() : list.size();
        return new FallPose(list, hold);
    }

    public int frameCount() { return frames.size(); }

    /** 인형을 보여주는 전체 길이 (마지막 프레임을 바닐라 자세 전환이 끝날 때까지 유지) */
    public int holdTicks() { return holdTicks; }

    /** tick 번째(0부터) 프레임 번호 */
    public int frameAt(int tick) {
        return Math.max(0, Math.min(frames.size() - 1, tick));
    }

    public Frame frame(int i) { return frames.get(i); }

    /** 몸 기준 좌표에서 부위 놓임 (scale = 개체 크기 배율) */
    public Placement place(int frame, Part part, double scale) {
        Frame f = frames.get(frame);
        Quaterniond body = new Quaterniond().rotationX(Math.toRadians(f.pitch()));
        double[] j = f.joints().getOrDefault(part, new double[3]);
        Quaterniond local = new Quaterniond().rotationXYZ(Math.toRadians(j[0]), Math.toRadians(j[1]), Math.toRadians(j[2]));
        Vector3d c = local.transform(new Vector3d(part.offset)).add(part.joint).mul(PX);
        body.transform(c).add(0, f.feetY(), f.feetZ()).mul(scale);
        return new Placement(c, new Quaterniond(body).mul(local));
    }

    /**
     * 바닐라 엎드린 자세 (AvatarRenderer: X축 -90° 회전 후 (0,-1,0.3) 이동, 몸 기준 좌표로 바꾸면 x 그대로, 높이 0.3-z, 앞 y-1).
     * 머리는 앞을 보도록 45° 들고, 팔은 머리 위로 뻗음 (정지 상태 기준).
     */
    public static Placement vanillaLying(Part part, double scale) {
        Vector3d stand = new Vector3d(part.offset).add(part.joint).mul(PX);
        Vector3d c = new Vector3d(stand.x, 0.3 - stand.z, stand.y - 1).mul(scale);
        Quaterniond body = new Quaterniond().rotationX(Math.PI / 2);
        Quaterniond local = new Quaterniond();
        if (part == Part.HEAD) local.rotationX(Math.toRadians(-45));
        if (part == Part.ARM_R || part == Part.ARM_L) local.rotationX(Math.PI);
        if (part != Part.BODY) {
            Vector3d j = new Vector3d(part.joint).mul(PX);
            Vector3d off = local.transform(new Vector3d(part.offset).mul(PX));
            Vector3d p = new Vector3d(j).add(off);
            c = new Vector3d(p.x, 0.3 - p.z, p.y - 1).mul(scale);
        }
        return new Placement(c, body.mul(local));
    }

    /**
     * 바닐라 누운 자세 (침대 없이 SLEEPING 인 마네킹, 몸 방향 φ = -yaw - 90).
     * LivingEntityRenderer: Y(φ)·Z(90)·Y(270) 를 서 있을 때 회전 Y(180-yaw) 대신 씀 →
     * 몸 기준 좌표로는 Ry(-90)·Rz(90)·Ry(90) (발을 축으로 뒤로 90° 누움, 얼굴이 위). 팔다리·머리는 똑바로. lift 만큼 띄움.
     */
    public static Placement vanillaBack(Part part, double scale, double lift) {
        Quaterniond r = new Quaterniond().rotationY(Math.toRadians(-90))
                .mul(new Quaterniond().rotationZ(Math.toRadians(90)))
                .mul(new Quaterniond().rotationY(Math.toRadians(90)));
        Vector3d stand = new Vector3d(part.offset).add(part.joint).mul(PX);
        Vector3d c = r.transform(stand).add(0, lift, 0).mul(scale);
        return new Placement(c, r);
    }

    /**
     * 바닐라 앉은 자세 (탈것에 탄 마네킹): 몸은 똑바로, 몸 기준 원점(발)이 seatY 높이.
     * 다리: 모델 xRot -1.4137167, yRot ±π/10, zRot ±0.0785 (ZYX) → 몸 기준 Rz(-z)·Ry(-y)·Rx(x).
     * 팔: xRot -π/5. 머리: 숙인 각도(마네킹 pitch).
     */
    public static Placement vanillaSit(Part part, double scale, double seatY, double headPitch) {
        Quaterniond local = new Quaterniond();
        switch (part) {
            case LEG_R -> local.rotationZ(-0.07853982).rotateY(-Math.PI / 10).rotateX(-1.4137167);
            case LEG_L -> local.rotationZ(0.07853982).rotateY(Math.PI / 10).rotateX(-1.4137167);
            case ARM_R, ARM_L -> local.rotationX(-Math.PI / 5);
            case HEAD -> local.rotationX(Math.toRadians(headPitch));
            default -> { }
        }
        Vector3d c = local.transform(new Vector3d(part.offset)).add(part.joint).mul(PX).add(0, seatY, 0).mul(scale);
        return new Placement(c, local);
    }

    /** 누운 마네킹의 바닐라 몸 방향 (yaw: 넘어지기 전 몸이 보던 방향) */
    public static float sleepingYaw(float yaw) {
        return (float) (((-yaw - 90) % 360 + 540) % 360 - 180);
    }

    /** 몸 기준 → 월드 (yaw: 바닐라 몸 방향, 도) */
    public static Vector3d toWorld(Vector3d local, float yaw) {
        return new Quaterniond().rotationY(Math.toRadians(-yaw)).transform(new Vector3d(local));
    }

    public static Quaterniond toWorld(Quaterniond local, float yaw) {
        return new Quaterniond().rotationY(Math.toRadians(-yaw)).mul(local);
    }

    /** 회전 차이 (라디안, 테스트용) */
    public static double angleBetween(Quaterniond a, Quaterniond b) {
        Matrix3d m = new Matrix3d().set(new Quaterniond(a).conjugate().mul(b));
        double tr = (m.m00 + m.m11 + m.m22 - 1) / 2;
        return Math.acos(Math.max(-1, Math.min(1, tr)));
    }
}
