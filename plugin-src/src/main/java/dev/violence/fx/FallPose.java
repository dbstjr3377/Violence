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

    public record Frame(double pitch, double feetY, double feetZ, Map<Part, double[]> joints) {}

    private final List<Frame> frames;
    private final int holdTicks;

    public FallPose(List<Frame> frames, int holdTicks) {
        if (frames.isEmpty()) throw new IllegalArgumentException("프레임이 없습니다");
        this.frames = List.copyOf(frames);
        this.holdTicks = Math.max(frames.size(), holdTicks);
    }

    public static FallPose load() {
        try (InputStream in = FallPose.class.getResourceAsStream("/fall.json")) {
            if (in == null) throw new IllegalStateException("fall.json 없음");
            return parse(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
        } catch (java.io.IOException e) {
            throw new IllegalStateException("fall.json 읽기 실패", e);
        }
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
            list.add(new Frame(o.get("pitch").getAsDouble(), feet.get(0).getAsDouble(), feet.get(1).getAsDouble(), joints));
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
