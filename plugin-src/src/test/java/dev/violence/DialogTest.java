package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.cutscene.CutsceneAssets;
import dev.violence.cutscene.DialogLayout;
import dev.violence.cutscene.Easing;
import dev.violence.mask.Mask;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;

/** 컷씬 다이얼로그: 이징, 화면 배치(전체 폭 0, 줄 가운데 정렬), 리소스팩이 만든 글리프 정보 */
class DialogTest {

    private static CutsceneAssets assets() throws Exception {
        return CutsceneAssets.load(Path.of("..", "bukkit", "plugins", "ViolenceCore", "cutscene.json"));
    }

    /** 조각들을 그대로 그렸을 때 각 줄의 [시작, 끝] 과 최종 펜 위치 */
    private static double[] simulate(CutsceneAssets a, List<DialogLayout.Piece> pieces, List<double[]> spans) {
        double pen = 0;
        for (DialogLayout.Piece p : pieces) {
            switch (p) {
                case DialogLayout.Space s -> pen += s.px();
                case DialogLayout.Text t -> {
                    double w = a.width(t.text());
                    spans.add(new double[]{pen, pen + w, t.line()});
                    pen += w;
                }
                case DialogLayout.Glyph g -> {
                    double w = g.c() == a.panelChar ? a.panelAdvance : a.portraitAdvance;
                    spans.add(new double[]{pen, pen + w, -1});
                    pen += w;
                }
            }
        }
        return new double[]{pen};
    }

    @Test
    void easingShapes() {
        assertEquals(0, Easing.outExpo(0), 1e-9);
        assertEquals(1, Easing.outExpo(1), 1e-9);
        assertTrue(Easing.outExpo(0.3) > 0.85, "easeOutExpo 는 앞부분에 대부분 움직임");
        assertEquals(0.5, Easing.inOutSine(0.5), 1e-9);
        assertEquals(0, Easing.inOutSine(0), 1e-9);
        double prev = -1;
        for (int i = 0; i <= 100; i++) {
            double v = Easing.outExpo(i / 100.0);
            assertTrue(v >= prev);
            prev = v;
        }
        // 흔들림: -15 → +15 → -15 반복, 양 끝에서 멈칫 (easeInOutSine)
        assertEquals(-15, Easing.sway(0, 20, 15), 1e-9);
        assertEquals(15, Easing.sway(20, 20, 15), 1e-9);
        assertEquals(-15, Easing.sway(40, 20, 15), 1e-9);
        assertEquals(0, Easing.sway(10, 20, 15), 1e-9);
        assertTrue(Math.abs(Easing.sway(1, 20, 15) - Easing.sway(0, 20, 15)) < Math.abs(Easing.sway(11, 20, 15) - Easing.sway(10, 20, 15)));
        for (int t = 0; t < 200; t++) assertTrue(Math.abs(Easing.sway(t * 0.37, 20, 15)) <= 15 + 1e-9);
        assertEquals(10, ((Easing.lerpAngle(350, 30, 0.5) % 360) + 360) % 360, 1e-9, "짧은 쪽(350→30 은 +40°)으로 돈다");
    }

    @Test
    void assetsMatchResourcePack() throws Exception {
        CutsceneAssets a = assets();
        assertEquals(8, a.letterboxFrames);
        for (Mask m : Mask.values()) {
            assertTrue(a.portraits.containsKey(m.name().toLowerCase(Locale.ROOT)), "초상화 없음: " + m);
        }
        assertTrue(a.portraits.containsKey("npc") && a.portraits.containsKey("unknown"));
        assertEquals(a.portraitBase("unknown"), a.portraitBase("없는이름"));
        int base = a.portraitBase("richard");
        assertEquals(base, a.portraitFrame(base, -15));
        assertEquals(base + a.portraitFrames - 1, a.portraitFrame(base, 15));
        assertEquals(base + a.portraitFrames / 2, a.portraitFrame(base, 0));
        // 글자 폭: 한글은 영문보다 넓고 공백은 좁음
        assertTrue(a.width('가') > a.width('a'));
        assertTrue(a.width(' ') < a.width('A'));
        assertTrue(a.width('가') > 8 && a.width('가') < 14);
    }

    @Test
    void dialogLinesAreCenteredAndTotalWidthIsZero() throws Exception {
        CutsceneAssets a = assets();
        DialogLayout l = new DialogLayout(a);
        List<String> lines = l.wrap("이게 꿈이라고 생각해? 그렇다면 이제 깨어날 시간이 된 것 같은데? YOU THINK THIS IS A DREAM?", DialogLayout.MAX_LINE, 2);
        assertEquals(2, lines.size());
        for (String s : lines) assertTrue(a.width(s) <= DialogLayout.MAX_LINE, s);
        int total = DialogLayout.length(lines);
        List<double[]> full = new java.util.ArrayList<>();
        double[] end = simulate(a, l.dialog(lines, total), full);
        assertEquals(0, end[0], 0.75, "전체 폭이 0 이어야 화면 중앙 기준으로 배치됨");
        for (double[] span : full) assertEquals(0, (span[0] + span[1]) / 2, 0.75, "줄 가운데 정렬");
        // 타자 효과: 글자가 늘어나도 각 줄의 시작 위치는 그대로
        for (int n = 1; n < total; n += 3) {
            List<double[]> part = new java.util.ArrayList<>();
            double[] e = simulate(a, l.dialog(lines, n), part);
            assertEquals(0, e[0], 0.75);
            for (double[] sp : part) assertEquals(full.get((int) sp[2])[0], sp[0], 0.75);
        }
    }

    @Test
    void wrapHandlesLongWordsAndNewlines() throws Exception {
        DialogLayout l = new DialogLayout(assets());
        List<String> w = l.wrap("가".repeat(60), 120, 5);
        assertTrue(w.size() >= 2);
        assertEquals(List.of("첫 줄", "둘째 줄"), l.wrap("첫 줄\\n둘째 줄", 300, 2));
        assertEquals(2, l.wrap("a\nb\nc", 300, 2).size());
    }

    @Test
    void panelSlidesInFromTheRight() throws Exception {
        CutsceneAssets a = assets();
        DialogLayout l = new DialogLayout(a);
        char frame = a.portraitFrame(a.portraitBase("richard"), 0);
        List<double[]> in = new java.util.ArrayList<>();
        double[] e = simulate(a, l.panel(0, frame), in);
        assertEquals(0, e[0], 1e-9);
        assertEquals(DialogLayout.PANEL_X, in.get(0)[0], 1e-9);
        assertEquals(DialogLayout.PORTRAIT_X, in.get(1)[0], 1e-9);
        List<double[]> out = new java.util.ArrayList<>();
        simulate(a, l.panel(1, frame), out);
        assertEquals(DialogLayout.PANEL_X + DialogLayout.SLIDE, out.get(0)[0], 1e-9);
        // 타이틀은 4배로 그려지므로 화면 밖(GUI 폭 절반 ≤ 약 320px = 80 글꼴 단위)에서 출발
        assertTrue((DialogLayout.PANEL_X + DialogLayout.SLIDE) * 4 > 480);
    }
}
