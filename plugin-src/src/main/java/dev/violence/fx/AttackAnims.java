package dev.violence.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 공격 상체 애니메이션 (attack.json, tools/attack_anims.py 가 만듦).
 * 공격하는 동안 실제 몸 대신 10부위 스킨 인형이 상체 동작을 한다 (FallPose 좌표, 틱 단위 프레임).
 * 프레임 w = 오른손이 쥐는 곳(몸 기준 블록)과 무기 회전 — ExecutionAnims.weapon 으로 무기를 놓는다.
 * 다리·머리는 FallService 가 틱마다 실제 몸의 걸음·시선으로 덮어쓴다.
 */
public final class AttackAnims {
    /** 한 동작: 인형 프레임 + 무기 놓임 + 쥐는 곳(모델 px) */
    public record Clip(ExecutionAnims.Track track, double[] grip) {
        public int length() { return track.length(); }
    }

    private final Map<String, Clip> guns = new HashMap<>();
    /** 묶음 → (A / B / STAB) → 프레임·무기 (쥐는 곳은 무기마다) */
    private final Map<String, Map<String, ExecutionAnims.Track>> melee = new HashMap<>();
    private final Map<String, String> groupOf = new HashMap<>();
    private final Map<String, double[]> grips = new HashMap<>();

    public static AttackAnims load() {
        try (InputStream in = AttackAnims.class.getResourceAsStream("/attack.json")) {
            if (in == null) throw new IllegalStateException("attack.json 없음");
            return new AttackAnims(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
        } catch (java.io.IOException e) {
            throw new IllegalStateException("attack.json 읽기 실패", e);
        }
    }

    AttackAnims(JsonObject root) {
        JsonObject g = root.getAsJsonObject("guns");
        for (String id : g.keySet()) {
            JsonObject o = g.getAsJsonObject(id);
            guns.put(id, new Clip(ExecutionAnims.trackOf(o.getAsJsonArray("frames")), vec(o.getAsJsonArray("grip"))));
        }
        JsonObject m = root.getAsJsonObject("melee");
        for (String group : m.keySet()) {
            Map<String, ExecutionAnims.Track> clips = new HashMap<>();
            JsonObject o = m.getAsJsonObject(group);
            for (String k : o.keySet()) clips.put(k, ExecutionAnims.trackOf(o.getAsJsonArray(k)));
            melee.put(group, clips);
        }
        JsonObject mg = root.getAsJsonObject("melee_group");
        for (String id : mg.keySet()) groupOf.put(id, mg.get(id).getAsString());
        JsonObject gr = root.getAsJsonObject("melee_grips");
        for (String id : gr.keySet()) grips.put(id, vec(gr.getAsJsonArray(id)));
    }

    private static double[] vec(JsonArray a) {
        return new double[] {a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()};
    }

    /** 총 쏘기 (겨눈 자세 → 반동 → 겨눈 자세), 없으면 null */
    public Clip gun(String id) {
        return guns.get(id);
    }

    /** 근접: kind = A(오→왼) / B(왼→오) / STAB, 없으면 null */
    public Clip melee(String id, String kind) {
        Map<String, ExecutionAnims.Track> clips = melee.get(groupOf.getOrDefault(id, "blunt"));
        if (clips == null) return null;
        ExecutionAnims.Track t = clips.get(kind);
        return t == null ? null : new Clip(t, grips.getOrDefault(id, new double[] {8, 3.5, 8}));
    }

    /** 테스트용 */
    static boolean isTrack(JsonElement e) {
        return e != null && e.isJsonArray();
    }
}
