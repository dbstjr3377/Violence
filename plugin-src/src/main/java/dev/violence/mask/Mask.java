package dev.violence.mask;

/** 연속 3/5킬 시 선택할 수 있는 가면 21종. */
public enum Mask {
    RICHARD("리처드", "닭", "효과 없음"),
    DON_JUAN("돈 후안", "말", "문 밀치기·발차기로 적 즉사"),
    GRAHAM("그레이엄", "토끼", "이동속도 증가"),
    DENNIS("데니스", "늑대", "맨손이면 단검 지급, F: 단검(5초)"),
    GEORGE("조지", "기린", "시야 확대 - 주변 적 윤곽 표시"),
    RUFUS("루퍼스", "코끼리", "총알 한 발을 버팀"),
    RAMI("라미", "낙타", "총을 주우면 탄창 추가"),
    WILLEM("윌럼", "원숭이", "Space: 서있는 적의 무기를 빼앗고 경직"),
    PETER("피터", "유니콘", "모든 무기 소음기 효과"),
    ZACK("잭", "개구리", "콤보 지속시간 증가"),
    RICK("릭", "여우", "총기 명중률 증가"),
    BRANDON("브랜던", "흑표범", "이동속도 대폭 증가"),
    EARL("얼", "바다코끼리", "총알 두 발을 버팀"),
    JAKE("제이크", "코브라", "투척 적중 시 적 즉사"),
    RICHTER("리히터", "쥐", "소음기 UZI 지급, F: 소음기 UZI(12초)"),
    PIG_BUTCHER("돼지 학살자", "돼지", "빠른 처형, 빠른 산탄총 연사"),
    CORY("코리", "얼룩말", "Space: 구르기"),
    MARK("마크", "곰", "64발 MP5 양손 소지"),
    TONY("토니", "호랑이", "맨주먹 즉사, 빠른 처형, 덩치도 맨주먹으로 눕힘"),
    DETECTIVE("형사", "중절모", "총기 처형, 명중률 상승, F: 샷건(12초)"),
    BIKER("바이커", "오토바이 헬멧", "맨손이면 중식도 지급, 빠른 이동, F: 중식도(5초)");

    private final String displayName;
    private final String animal;
    private final String description;

    Mask(String displayName, String animal, String description) {
        this.displayName = displayName;
        this.animal = animal;
        this.description = description;
    }

    public String displayName() { return displayName; }
    public String animal() { return animal; }
    public String description() { return description; }
    public String id() { return name().toLowerCase(java.util.Locale.ROOT); }
    public String model() { return "violence:mask/" + id(); }

    /** 기본 이동속도 배율 */
    public double speedMultiplier() {
        return switch (this) {
            case GRAHAM -> 1.15;
            case BRANDON -> 1.32;
            case BIKER -> 1.15;
            default -> 1.0;
        };
    }

    /** 총기 탄퍼짐 배율 (낮을수록 정확) */
    public double spreadMultiplier() {
        return switch (this) {
            case RICK -> 0.45;
            case DETECTIVE -> 0.6;
            default -> 1.0;
        };
    }

    public int bulletShield() {
        return switch (this) {
            case RUFUS -> 1;
            case EARL -> 2;
            default -> 0;
        };
    }

    public boolean fastExecution() {
        return this == PIG_BUTCHER || this == TONY;
    }

    public static Mask parse(String s) {
        for (Mask m : values()) if (m.name().equalsIgnoreCase(s) || m.displayName.equals(s)) return m;
        return null;
    }
}
