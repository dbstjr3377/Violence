package dev.violence.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.violence.mask.Mask;
import dev.violence.weapon.WeaponType;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.joml.Quaterniond;
import org.joml.Vector3d;

/**
 * 처형 애니메이션 (execution.json, tools/exec_anims.py 가 만듦). 순수 계산이라 서버 없이 테스트 가능.
 *
 * 처형자와 피처형자 모두 10부위 인형(팔꿈치·무릎이 있는 두 마디 팔다리)으로 움직인다 (FallPose 와 같은 좌표).
 *  - 처형자 기준점 = 누운 적의 발에서 머리 쪽으로 anchor 블록, 머리 쪽을 봄
 *  - 피처형자 = 누운 대역 자리, 등으로 누운 자세 + 머리·팔 움직임
 *  - 무기 = 프레임마다 w = [x, y, z, qx, qy, qz, qw] (오른손이 쥐는 곳, 몸 기준 블록 + 회전).
 *    팔은 만들 때 두 마디 IK 로 손을 손잡이에 붙여 두었으므로 무기만 그대로 놓으면 됨 (none / right / both)
 * 왼클릭 처형(hits)은 ready + strike(한 번 칠 때, impact 프레임에 머리에 닿음), 자동(auto)은 full + impacts + kill.
 */
public final class ExecutionAnims {
    public enum Style { HITS, AUTO }

    /** 인형 한 줄(처형자 또는 피처형자)의 프레임 + 무기 놓임 (프레임마다 [x,y,z,qx,qy,qz,qw], 없으면 null) */
    public record Track(FallPose pose, double[][] weapon) {
        public int length() { return pose.frameCount(); }
    }

    public record Event(int tick, String kind) {}

    public record Anim(String name, double anchor, String weapon, Style style,
                       Track readyExec, Track readyVictim, Track strikeExec, Track strikeVictim, int impact,
                       Track fullExec, Track fullVictim, int[] impacts, int kill, List<Event> events) {
        public boolean hits() { return style == Style.HITS; }
        public int strikeLength() { return strikeExec == null ? 0 : strikeExec.length(); }
        public int fullLength() { return fullExec == null ? 0 : fullExec.length(); }
    }

    private final Map<String, Anim> anims = new HashMap<>();
    private final Map<String, String> groupOf = new HashMap<>();
    private final Set<String> stompMasks = new HashSet<>();
    private final Map<String, double[]> grips = new HashMap<>();

    public static ExecutionAnims load() {
        try (InputStream in = ExecutionAnims.class.getResourceAsStream("/execution.json")) {
            if (in == null) throw new IllegalStateException("execution.json 없음");
            return new ExecutionAnims(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
        } catch (java.io.IOException e) {
            throw new IllegalStateException("execution.json 읽기 실패", e);
        }
    }

    ExecutionAnims(JsonObject root) {
        JsonObject groups = root.getAsJsonObject("groups");
        for (String g : groups.keySet()) {
            for (JsonElement id : groups.getAsJsonArray(g)) groupOf.put(id.getAsString(), g);
        }
        for (JsonElement m : root.getAsJsonArray("stomp_masks")) stompMasks.add(m.getAsString());
        JsonObject gr = root.getAsJsonObject("grips");
        for (String id : gr.keySet()) {
            JsonArray a = gr.getAsJsonArray(id);
            grips.put(id, new double[] {a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()});
        }
        JsonObject all = root.getAsJsonObject("anims");
        for (String name : all.keySet()) {
            JsonObject o = all.getAsJsonObject(name);
            Style style = "auto".equals(o.get("style").getAsString()) ? Style.AUTO : Style.HITS;
            Track re = null, rv = null, se = null, sv = null, fe = null, fv = null;
            int impact = -1, kill = -1;
            int[] impacts = new int[0];
            List<Event> events = new ArrayList<>();
            if (o.has("ready")) {
                JsonObject r = o.getAsJsonObject("ready");
                re = track(single(r.get("exec")));
                rv = track(single(r.get("victim")));
            }
            if (o.has("strike")) {
                JsonObject s = o.getAsJsonObject("strike");
                se = track(s.getAsJsonArray("exec"));
                sv = track(s.getAsJsonArray("victim"));
                impact = s.get("impact").getAsInt();
            }
            if (o.has("full")) {
                JsonObject f = o.getAsJsonObject("full");
                fe = track(f.getAsJsonArray("exec"));
                fv = track(f.getAsJsonArray("victim"));
                JsonArray im = f.getAsJsonArray("impacts");
                impacts = new int[im.size()];
                for (int i = 0; i < im.size(); i++) impacts[i] = im.get(i).getAsInt();
                kill = f.get("kill").getAsInt();
                if (f.has("events")) {
                    for (JsonElement ev : f.getAsJsonArray("events")) {
                        JsonObject e = ev.getAsJsonObject();
                        events.add(new Event(e.get("t").getAsInt(), e.get("kind").getAsString()));
                    }
                }
            }
            anims.put(name, new Anim(name, o.get("anchor").getAsDouble(), o.get("weapon").getAsString(), style,
                    re, rv, se, sv, impact, fe, fv, impacts, kill, List.copyOf(events)));
        }
    }

    private static JsonArray single(JsonElement e) {
        JsonArray a = new JsonArray();
        a.add(e);
        return a;
    }

    private static Track track(JsonArray frames) {
        JsonObject wrap = new JsonObject();
        wrap.add("frames", frames);
        FallPose pose = FallPose.parse(wrap);
        double[][] weapon = new double[frames.size()][];
        for (int i = 0; i < frames.size(); i++) {
            JsonObject f = frames.get(i).getAsJsonObject();
            if (!f.has("w")) continue;
            JsonArray w = f.getAsJsonArray("w");
            weapon[i] = new double[7];
            for (int k = 0; k < 7; k++) weapon[i][k] = w.get(k).getAsDouble();
        }
        return new Track(pose, weapon);
    }

    public Anim get(String name) { return anims.get(name); }

    public Map<String, Anim> all() { return Map.copyOf(anims); }

    /** 무기 묶음 이름 (blunt / heavy / light / blade), 없으면 null */
    public String groupOf(String weaponId) { return groupOf.get(weaponId); }

    /**
     * 처형 동작 고르기: 맨손이면 머리 박기 (코브라·돼지·곰 가면이면 밟기), 근접 무기는 묶음별.
     * 총·투척 무기는 버리고 맨손으로 처형하므로 부르는 쪽에서 맨손으로 바꿔 넘긴다.
     */
    public String animFor(WeaponType t, Mask mask) {
        if (t == null || t.isFist()) return mask != null && stompMasks.contains(mask.name()) ? "stomp" : "fist";
        String g = groupOf.get(t.id());
        return g != null ? g : "blunt";
    }

    /** 무기 손잡이(쥐는 곳) 모델 좌표 (px) */
    public double[] grip(String weaponId) {
        return grips.getOrDefault(weaponId, new double[] {8, 3.5, 8});
    }

    /** 무기 크기 (손에 든 3인칭 무기와 같음: 0.85 × 플레이어 모델 0.9375) */
    public static final double WEAPON_SCALE = 0.85 * 0.9375;

    /** 그 프레임의 오른손 쥐는 곳 (몸 기준, 블록) — 무기가 없으면 null */
    public static Vector3d grip(Track t, int frame, double scale) {
        double[] w = t.weapon()[frame];
        return w == null ? null : new Vector3d(w[0], w[1], w[2]).mul(scale);
    }

    /** 그 프레임의 무기 회전 (모델 +Y = 손잡이→끝, +Z = 앞면) — 무기가 없으면 null */
    public static Quaterniond weaponRotation(Track t, int frame) {
        double[] w = t.weapon()[frame];
        return w == null ? null : new Quaterniond(w[3], w[4], w[5], w[6]).normalize();
    }

    /**
     * 오른손 무기 놓임 (몸 기준 좌표): 중심(모델 원점이 놓일 곳)과 회전.
     * 쥐는 곳(grip, 모델 px)이 프레임의 w 위치에 오도록 모델 원점을 옮김.
     */
    public static FallPose.Placement weapon(Track t, int frame, double scale, double[] grip) {
        Vector3d hand = grip(t, frame, scale);
        Quaterniond r = weaponRotation(t, frame);
        if (hand == null) return null;
        double s = WEAPON_SCALE * scale;
        Vector3d g = new Vector3d(grip[0] / 16 - 0.5, grip[1] / 16 - 0.5, grip[2] / 16 - 0.5).mul(s);
        Vector3d origin = hand.sub(r.transform(g, new Vector3d()), new Vector3d());
        return new FallPose.Placement(origin, r);
    }
}
