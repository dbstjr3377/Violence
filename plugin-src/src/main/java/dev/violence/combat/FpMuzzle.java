package dev.violence.combat;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 총마다 총구 자리 (tools/build_pack.py 가 만든 fp_muzzle.json).
 * fp = 1인칭 총 모델 총구의 시점 좌표 (블록: 오른쪽, 위, 앞이 -z). 손 모델은 FOV 70 으로 그려지므로
 * 월드에 궤적을 놓을 때는 보는 사람 FOV 에 맞춰 옆·위 성분을 늘려 화면에서 같은 자리에 오게 한다.
 * tp = 3인칭 손에서 총구까지 길이 (블록).
 */
public final class FpMuzzle {
    private static Map<String, double[]> fp;
    private static Map<String, Double> tp;

    private FpMuzzle() {
    }

    private static void load() {
        if (fp != null) return;
        fp = new HashMap<>();
        tp = new HashMap<>();
        try (var in = FpMuzzle.class.getResourceAsStream("/fp_muzzle.json")) {
            if (in == null) return;
            JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
            for (var e : o.entrySet()) {
                JsonObject g = e.getValue().getAsJsonObject();
                var a = g.getAsJsonArray("fp");
                fp.put(e.getKey(), new double[]{a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()});
                tp.put(e.getKey(), g.get("tp").getAsDouble());
            }
        } catch (java.io.IOException | RuntimeException ignored) {
            // 표가 없으면 예전 고정 자리
        }
    }

    /** 1인칭 총구 (오른쪽, 위, z) — 보는 사람 FOV 에 맞춤. 없으면 null */
    public static double[] fp(String gunId, double viewFov) {
        load();
        double[] v = fp.get(gunId);
        if (v == null) return null;
        double k = Math.tan(Math.toRadians(viewFov / 2)) / Math.tan(Math.toRadians(35));
        return new double[]{v[0] * k, v[1] * k, v[2]};
    }

    public static double tpLength(String gunId) {
        load();
        return tp.getOrDefault(gunId, 0.35);
    }
}
