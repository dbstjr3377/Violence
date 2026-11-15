package dev.violence.logic;

/**
 * 문의 회전. 각도(도)는 -max..+max, 0 이 닫힘.
 * - F 로 열고 닫기: 목표 각도로 부드럽게 돌아감 (사람을 쓰러뜨리지 않는 빠르기)
 * - 발차기: 각속도로 세게 돌아 끝에 닿으면 살짝 튕기고, 멈춘 자리에 그대로 열려 있음
 */
public final class DoorPhysics {
    public static final double MAX_ANGLE = 105;
    /** F 로 열면 이만큼 열림 */
    public static final double OPEN_ANGLE = 95;
    public static final double FRICTION = 0.80;
    public static final double CLOSED_EPS = 12;
    /** F 로 여닫을 때 최대 회전 속도 (도/틱, isDangerous 의 14 보다 작아야 사람을 쓰러뜨리지 않음) */
    public static final double SWING_SPEED = 11;

    private double angle;
    private double velocity;
    /** 목표 각도 (F 로 여닫기). NaN 이면 발차기처럼 각속도로만 움직임 */
    private double target = 0;

    public double angle() { return angle; }
    public double velocity() { return velocity; }
    public double target() { return target; }

    /** direction: +1 또는 -1 방향으로 strength(도/틱) 만큼 민다 (발차기). 더 빠른 쪽만 반영. */
    public void push(int direction, double strength) {
        target = Double.NaN;
        double t = direction * strength;
        if (direction > 0) velocity = Math.max(velocity, t);
        else velocity = Math.min(velocity, t);
    }

    /** 목표 각도로 부드럽게 돌아감 (F 로 열기·닫기) */
    public void swingTo(double targetAngle) {
        target = Math.max(-MAX_ANGLE, Math.min(MAX_ANGLE, targetAngle));
        velocity = 0;
    }

    public void tick() {
        if (!Double.isNaN(target)) {
            double d = target - angle;
            if (Math.abs(d) < 0.01) {
                angle = target;
                return;
            }
            // 처음엔 빠르게, 끝에서 천천히 (최소 2도/틱)
            double step = Math.min(Math.abs(d), Math.max(2.0, Math.min(SWING_SPEED, Math.abs(d) * 0.45)));
            angle += Math.signum(d) * step;
            return;
        }
        angle += velocity;
        if (angle > MAX_ANGLE) { angle = MAX_ANGLE; velocity = -velocity * 0.2; }
        if (angle < -MAX_ANGLE) { angle = -MAX_ANGLE; velocity = -velocity * 0.2; }
        velocity *= FRICTION;
        if (Math.abs(velocity) < 0.05) {
            velocity = 0;
            target = angle;   // 발차기로 열린 문은 멈춘 자리에 그대로
        }
    }

    public boolean isClosed() { return Math.abs(angle) < CLOSED_EPS; }

    /** 열려 있거나 열리는 중 (닫히는 중이면 false) */
    public boolean isOpen() {
        return Double.isNaN(target) ? Math.abs(angle) >= CLOSED_EPS : Math.abs(target) >= CLOSED_EPS;
    }

    /** 부딪힌 사람을 쓰러뜨릴 만큼 빠르게 도는가 (발차기) */
    public boolean isDangerous() { return Math.abs(velocity) >= 14; }

    public boolean isMoving() {
        return velocity != 0 || (!Double.isNaN(target) && Math.abs(target - angle) >= 0.01);
    }

    public void set(double angle, double velocity) {
        this.angle = angle;
        this.velocity = velocity;
        if (velocity != 0) target = Double.NaN;
    }
}
