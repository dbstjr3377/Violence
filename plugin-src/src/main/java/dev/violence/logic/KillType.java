package dev.violence.logic;

/** 처치 방식. 어려운 방식일수록 점수가 높다 (총 → 투척 → 근접 → 맨손 → 처형). */
public enum KillType {
    GUN("총기", 100),
    THROW("투척", 200),
    MELEE("근접", 300),
    FIST("맨손", 400),
    EXECUTION("처형", 500),
    DOOR("문", 350);

    private final String display;
    private final int defaultPoints;

    KillType(String display, int defaultPoints) {
        this.display = display;
        this.defaultPoints = defaultPoints;
    }

    public String display() { return display; }
    public int defaultPoints() { return defaultPoints; }

    public static KillType parse(String s) {
        for (KillType t : values()) if (t.name().equalsIgnoreCase(s)) return t;
        return GUN;
    }
}
