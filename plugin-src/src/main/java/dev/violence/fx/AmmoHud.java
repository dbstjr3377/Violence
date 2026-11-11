package dev.violence.fx;

import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponType;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.ShadowColor;
import net.kyori.adventure.text.format.TextColor;

/**
 * 우측 하단 탄수 표시 (액션바에 실어 보내고, 리소스팩 text.vsh 쉐이더가 화면 오른쪽 아래로 옮김).
 *  - 총: "현재탄수/총탄수" (탄창 무기는 탄창 잔탄/남은 전체), 다 쓰면 "탄 없음!"
 *  - 샷건(산탄): 숫자 대신 탄피 아이콘 게이지 (남은 탄 = 빨간 탄피, 쓴 탄 = 빈 탄피)
 * 쉐이더는 아래의 "표시 색"(정확한 RGB 값)으로 옮길 글자를 알아본다. 그림자도 정해진 색으로 보내 함께 옮긴다.
 * 탄수 글의 오른쪽 끝이 늘 화면 가운데에 오도록, 액션바에 같은 너비의 글을 "숨김 색"으로 함께 붙인다 (쉐이더가 화면 밖으로 치움).
 * 그래서 탄수 길이와 상관없이 오른쪽 정렬로 화면 오른쪽 아래에 붙는다.
 * 색 값은 tools/shaders/core/text.vsh 와 같아야 함.
 */
public final class AmmoHud {
    private AmmoHud() {}

    public static final int WHITE = 0xFDFBF9;
    public static final int YELLOW = 0xFDE14B;
    public static final int RED = 0xFD2D39;
    public static final int SHADOW = 0x3F3E3D;
    public static final int HIDE = 0x010203;

    /** 탄피 아이콘 (hud 글꼴): 남은 탄 / 쓴 탄 */
    public static final String SHELL = "";
    public static final String SHELL_EMPTY = "";

    /** 산탄총(탄피 게이지로 보이는 총) */
    public static boolean shellGauge(WeaponType t) {
        return t.isGun() && t.pelletsMax() > 1;
    }

    /** 표시할 글 (마커 색 없이 내용만): 총이 아니면 null */
    public static String text(WeaponType t, WeaponInstance w, WeaponInstance offhand) {
        if (!t.isGun() || w == null) return null;
        int ammo = w.ammo() + (offhand != null ? offhand.ammo() : 0);
        if (ammo <= 0) return "탄 없음!";
        if (shellGauge(t)) {
            int max = t.ammo() * (offhand != null ? 2 : 1);
            return SHELL.repeat(Math.min(ammo, max)) + SHELL_EMPTY.repeat(Math.max(0, max - ammo));
        }
        if (t.hasMagazine()) return w.mag() + "/" + ammo;
        int max = t.ammo() * (offhand != null ? 2 : 1);
        return ammo + "/" + max;
    }

    /** 우측 하단에 놓일 글 (마커 색 + 마커 그림자). 재장전 중이면 노란색 */
    public static Component marked(WeaponType t, WeaponInstance w, WeaponInstance offhand, boolean reloading) {
        String s = text(t, w, offhand);
        if (s == null) return Component.empty();
        int ammo = w.ammo() + (offhand != null ? offhand.ammo() : 0);
        int col = ammo <= 0 ? RED : (reloading || (!shellGauge(t) && ammo <= Math.max(1, t.ammo() / 4)) ? YELLOW : WHITE);
        return Component.text(s).font(Glyphs.HUD).color(TextColor.color(col)).shadowColor(ShadowColor.shadowColor(0xFF000000 | SHADOW));
    }

    /** 탄수 글과 같은 너비의 보이지 않는 짝 */
    public static Component hidden(WeaponType t, WeaponInstance w, WeaponInstance offhand) {
        String s = text(t, w, offhand);
        return s == null ? Component.empty() : hiddenText(s);
    }

    /** 보이지 않는 글 (hud 글꼴, 너비만 차지) */
    public static Component hiddenText(String s) {
        if (s == null || s.isEmpty()) return Component.empty();
        return Component.text(s).font(Glyphs.HUD).color(TextColor.color(HIDE)).shadowColor(ShadowColor.shadowColor(0));
    }
}
