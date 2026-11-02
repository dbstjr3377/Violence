package dev.violence.cutscene;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.Reader;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 리소스팩 생성기(tools/pack_cutscene.py)가 만든 cutscene.json: 글리프 번호와 글자 폭.
 * 대사를 화면 가운데에 맞추려면 서버가 글자 폭을 알아야 해서 함께 만든다.
 */
public final class CutsceneAssets {
    public final int letterboxFrames;
    public final char panelChar;
    public final int panelAdvance;
    public final int portraitAdvance;
    public final int portraitFrames;
    public final double portraitSway;
    public final double dialogSize;
    /** 자간: 대사 글자마다 뒤에 붙이는 좁은 공백 글리프 */
    public final char trackChar;
    public final double track;
    public final Map<String, Integer> portraits = new LinkedHashMap<>();
    private final Map<Character, Double> ascii = new LinkedHashMap<>();
    private final Map<Character, Double> extra = new LinkedHashMap<>();
    private final double hangulDefault;
    private final double fallback;
    private final short[] hangul;

    private CutsceneAssets(JsonObject o) {
        letterboxFrames = o.get("letterbox_frames").getAsInt();
        JsonObject panel = o.getAsJsonObject("panel");
        panelChar = (char) panel.get("char").getAsInt();
        panelAdvance = panel.get("advance").getAsInt();
        JsonObject p = o.getAsJsonObject("portrait");
        portraitAdvance = p.get("advance").getAsInt();
        portraitFrames = p.get("frames").getAsInt();
        portraitSway = p.get("sway").getAsDouble();
        for (Map.Entry<String, JsonElement> e : p.getAsJsonObject("chars").entrySet()) portraits.put(e.getKey(), e.getValue().getAsInt());
        JsonObject d = o.getAsJsonObject("dialog");
        dialogSize = d.get("size").getAsDouble();
        if (d.has("track")) {
            trackChar = (char) d.getAsJsonObject("track").get("char").getAsInt();
            track = d.getAsJsonObject("track").get("advance").getAsDouble();
        } else {
            trackChar = 0;
            track = 0;
        }
        JsonObject m = d.getAsJsonObject("metrics");
        for (Map.Entry<String, JsonElement> e : m.getAsJsonObject("ascii").entrySet()) ascii.put(e.getKey().charAt(0), e.getValue().getAsDouble());
        if (m.has("extra")) {
            for (Map.Entry<String, JsonElement> e : m.getAsJsonObject("extra").entrySet()) extra.put(e.getKey().charAt(0), e.getValue().getAsDouble());
        }
        hangulDefault = m.get("hangul").getAsDouble();
        fallback = m.get("default").getAsDouble();
        short[] table = null;
        if (m.has("hangul_table")) {
            byte[] raw = Base64.getDecoder().decode(m.get("hangul_table").getAsString());
            ByteBuffer bb = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
            table = new short[raw.length / 2];
            for (int i = 0; i < table.length; i++) table[i] = bb.getShort();
        }
        hangul = table;
    }

    public static CutsceneAssets load(Path file) throws IOException {
        try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            return new CutsceneAssets(JsonParser.parseReader(r).getAsJsonObject());
        }
    }

    /** 대사 글꼴에서 한 글자가 차지하는 폭 (GUI 픽셀, 자간 포함) */
    public double width(char c) {
        return glyphWidth(c) + track;
    }

    /** 자간을 넣은 실제 출력 문자열 */
    public String tracked(String s) {
        if (trackChar == 0) return s;
        StringBuilder b = new StringBuilder(s.length() * 2);
        for (int i = 0; i < s.length(); i++) b.append(s.charAt(i)).append(trackChar);
        return b.toString();
    }

    private double glyphWidth(char c) {
        Double a = ascii.get(c);
        if (a != null) return a;
        if (c >= 0xAC00 && c <= 0xD7A3) {
            if (hangul != null && c - 0xAC00 < hangul.length) return (hangul[c - 0xAC00] & 0xFFFF) / 1000.0;
            return hangulDefault;
        }
        Double e = extra.get(c);
        return e != null ? e : fallback;
    }

    public double width(String s) {
        double w = 0;
        for (int i = 0; i < s.length(); i++) w += width(s.charAt(i));
        return w;
    }

    /** 초상화 이름 → 글리프 시작 번호 (없으면 unknown) */
    public int portraitBase(String id) {
        Integer b = portraits.get(id == null ? "unknown" : id.toLowerCase(java.util.Locale.ROOT));
        if (b == null) b = portraits.get("unknown");
        return b == null ? -1 : b;
    }

    /** 흔들림 각도(도) → 프레임 글리프 */
    public char portraitFrame(int base, double angle) {
        double t = (angle + portraitSway) / (2 * portraitSway);
        int f = (int) Math.round(Easing.clamp01(t) * (portraitFrames - 1));
        return (char) (base + f);
    }
}
