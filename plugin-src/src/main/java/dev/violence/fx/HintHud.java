package dev.violence.fx;

import java.util.HashMap;
import java.util.Map;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.ShadowColor;
import net.kyori.adventure.text.format.TextColor;

/**
 * 조준점 오른쪽 상호작용 안내 ("F 문 열기", "Space 발차기").
 * 리소스팩에서 미리 그린 글리프(build_pack.HINTS)를 액션바에 정해진 색으로 싣고, text.vsh 쉐이더가 조준점 옆 줄로 옮긴다.
 * 글리프 뒤에 같은 폭의 음수 공백을 붙여 액션바의 다른 글(탄수·가면 이름)의 자리는 그대로 둔다.
 * 그래서 안내는 늘 "탄수가 끝나는 자리 = 화면 가운데"에서 시작하고, 쉐이더가 오른쪽으로 조금 옮긴다.
 * 색 값은 tools/shaders/core/text.vsh 와 같아야 함.
 */
public final class HintHud {
    private HintHud() {}

    /** 첫째 줄 / 둘째 줄 표시 색 */
    public static final int ROW1 = 0xFAFBFC;
    public static final int ROW2 = 0xF9FBFC;

    public enum Hint { OPEN, CLOSE, KICK, KICK_CD }

    private record Glyph(String ch, int advance) {}

    private static Map<Hint, Glyph> glyphs;

    private static synchronized Map<Hint, Glyph> glyphs() {
        if (glyphs != null) return glyphs;
        Map<Hint, Glyph> m = new HashMap<>();
        try (var in = HintHud.class.getResourceAsStream("/hint_glyphs.json")) {
            if (in != null) {
                var o = com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
                for (Hint h : Hint.values()) {
                    var g = o.getAsJsonObject(h.name().toLowerCase(java.util.Locale.ROOT));
                    if (g != null) m.put(h, new Glyph(g.get("char").getAsString(), g.get("advance").getAsInt()));
                }
            }
        } catch (java.io.IOException ignored) {
            // 폭표가 없으면 안내를 띄우지 않음
        }
        glyphs = m;
        return m;
    }

    /** 안내 한 줄 (row 0 = 첫째 줄, 1 = 둘째 줄). 폭은 0 (뒤에 음수 공백) */
    public static Component hint(Hint h, int row) {
        Glyph g = glyphs().get(h);
        if (g == null) return Component.empty();
        return Component.empty()
                .append(Component.text(g.ch()).font(Glyphs.HUD).color(TextColor.color(row == 0 ? ROW1 : ROW2))
                        .shadowColor(ShadowColor.shadowColor(0)))
                .append(Glyphs.space(-g.advance()));
    }
}
