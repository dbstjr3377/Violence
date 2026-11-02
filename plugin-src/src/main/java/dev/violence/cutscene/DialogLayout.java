package dev.violence.cutscene;

import java.util.ArrayList;
import java.util.List;

/**
 * 컷씬 화면 배치 (순수 계산). 마인크래프트는 타이틀/액션바 문자열을 전체 폭의 가운데에 맞춰 그리므로,
 * 공백 글리프로 위치를 옮긴 뒤 마지막에 펜을 0 으로 되돌려 "전체 폭 0" 으로 만든다.
 * 그러면 모든 조각을 화면 중앙 기준 좌표로 직접 놓을 수 있다.
 */
public final class DialogLayout {
    /** 출력 조각: 공백(px), 대사 줄, 패널/초상화 글리프 */
    public sealed interface Piece permits Space, Text, Glyph {}
    public record Space(int px) implements Piece {}
    public record Text(String text, int line) implements Piece {}
    public record Glyph(char c) implements Piece {}

    /** 대사 상자에 들어가는 한 줄 최대 폭 (GUI 픽셀) */
    public static final double MAX_LINE = 300;
    /** 패널 왼쪽 변 위치 (타이틀 글꼴 단위, 화면 중앙 기준; 타이틀은 4배로 그려짐) */
    public static final int PANEL_X = 16;
    /** 패널 안 초상화 왼쪽 위치 */
    public static final int PORTRAIT_X = 26;
    /** 패널이 화면 밖에서 들어오는 거리 */
    public static final int SLIDE = 110;

    private final CutsceneAssets a;

    public DialogLayout(CutsceneAssets a) {
        this.a = a;
    }

    /** 단어 단위로 줄바꿈 (한 단어가 너무 길면 글자 단위). maxLines 를 넘는 부분은 버린다. */
    public List<String> wrap(String text, double maxWidth, int maxLines) {
        List<String> lines = new ArrayList<>();
        for (String para : text.replace("\\n", "\n").split("\n", -1)) {
            StringBuilder line = new StringBuilder();
            for (String word : para.split(" ", -1)) {
                String candidate = line.isEmpty() ? word : line + " " + word;
                if (a.width(candidate) <= maxWidth) {
                    line.setLength(0);
                    line.append(candidate);
                    continue;
                }
                if (!line.isEmpty()) {
                    lines.add(line.toString());
                    line.setLength(0);
                }
                for (int i = 0; i < word.length(); i++) {
                    if (a.width(line.toString() + word.charAt(i)) > maxWidth && !line.isEmpty()) {
                        lines.add(line.toString());
                        line.setLength(0);
                    }
                    line.append(word.charAt(i));
                }
            }
            lines.add(line.toString());
        }
        while (lines.size() > 1 && lines.getLast().isEmpty()) lines.removeLast();
        return lines.size() > maxLines ? new ArrayList<>(lines.subList(0, maxLines)) : lines;
    }

    /**
     * 액션바 대사: 줄마다 화면 가운데 정렬. revealed 글자까지만 찍는다(타자 효과).
     * 줄 위치는 전체 문장 폭으로 미리 정하므로 글자가 늘어나도 흔들리지 않는다.
     */
    public List<Piece> dialog(List<String> lines, int revealed) {
        List<Piece> out = new ArrayList<>();
        double pen = 0;     // 실제 글자 폭(소수) 포함 현재 위치
        int left = revealed;
        for (int i = 0; i < lines.size() && left > 0; i++) {
            String full = lines.get(i);
            double start = -a.width(full) / 2;
            int move = (int) Math.round(start - pen);
            if (move != 0) out.add(new Space(move));
            pen += move;
            String shown = full.substring(0, Math.min(full.length(), left));
            left -= shown.length();
            if (!shown.isEmpty()) {
                out.add(new Text(shown, i));
                pen += a.width(shown);
            }
        }
        int back = (int) Math.round(-pen);
        if (back != 0) out.add(new Space(back));
        return out;
    }

    /** 글자 수 (타자 효과 진행 기준) */
    public static int length(List<String> lines) {
        int n = 0;
        for (String s : lines) n += s.length();
        return n;
    }

    /**
     * 타이틀: 오른쪽 패널 + 흔들리는 초상화.
     * @param slide 0 = 제자리, 1 = 화면 밖 (오른쪽)
     * @param portrait 초상화 프레임 글리프 (없으면 0)
     */
    public List<Piece> panel(double slide, char portrait) {
        List<Piece> out = new ArrayList<>();
        int off = (int) Math.round(SLIDE * Easing.clamp01(slide));
        int pen = 0;
        out.add(new Space(PANEL_X + off));
        pen += PANEL_X + off;
        out.add(new Glyph(a.panelChar));
        pen += a.panelAdvance;
        if (portrait != 0) {
            int to = PORTRAIT_X + off;
            out.add(new Space(to - pen));
            pen = to;
            out.add(new Glyph(portrait));
            pen += a.portraitAdvance;
        }
        out.add(new Space(-pen));
        return out;
    }
}
