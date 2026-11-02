package dev.violence.logic;

/**
 * 문의 회전 물리. 각도(도)는 -max..+max, 0 이 닫힘.
 * 밀면 각속도가 생기고 마찰로 멈춘다. 끝에 닿으면 살짝 튕긴다.
 */
public final class DoorPhysics {
    public static final double MAX_ANGLE = 105;
    public static final double FRICTION = 0.80;
    public static final double CLOSED_EPS = 12;

    private double angle;
    private double velocity;

    public double angle() { return angle; }
    public double velocity() { return velocity; }

    /** direction: +1 또는 -1 방향으로 strength(도/틱) 만큼 민다. 더 빠른 쪽만 반영. */
    public void push(int direction, double strength) {
        double target = direction * strength;
        if (direction > 0) velocity = Math.max(velocity, target);
        else velocity = Math.min(velocity, target);
    }

    public void tick() {
        angle += velocity;
        if (angle > MAX_ANGLE) { angle = MAX_ANGLE; velocity = -velocity * 0.2; }
        if (angle < -MAX_ANGLE) { angle = -MAX_ANGLE; velocity = -velocity * 0.2; }
        velocity *= FRICTION;
        if (Math.abs(velocity) < 0.05) velocity = 0;
    }

    public boolean isClosed() { return Math.abs(angle) < CLOSED_EPS; }

    /** 부딪힌 사람을 쓰러뜨릴 만큼 빠르게 도는가 (발차기 등) */
    public boolean isDangerous() { return Math.abs(velocity) >= 14; }

    public boolean isMoving() { return velocity != 0; }

    public void set(double angle, double velocity) {
        this.angle = angle;
        this.velocity = velocity;
    }
}
