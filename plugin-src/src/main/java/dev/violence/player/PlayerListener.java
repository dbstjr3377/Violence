package dev.violence.player;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.combat.CombatState;
import io.papermc.paper.event.player.PlayerArmSwingEvent;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockDamageEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.FoodLevelChangeEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.player.PlayerDropItemEvent;
import org.bukkit.event.player.PlayerInputEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerItemHeldEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerSwapHandItemsEvent;
import org.bukkit.event.player.PlayerToggleSprintEvent;
import org.bukkit.inventory.EquipmentSlot;

/**
 * 플레이어 입력 → 전투 동작 연결.
 * 왼클릭 = 사용, 우클릭 = 던지기→줍기, Space = 올라타기/발차기/가면, F = 가면 능력,
 * 1번 칸 외 슬롯/F키/아이템 버리기는 모두 막는다.
 */
public final class PlayerListener implements Listener {
    private final ViolencePlugin plugin;

    public PlayerListener(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    private PlayerCombatant pc(Player p) {
        Arena a = plugin.arena();
        return a == null ? null : a.players.get(p.getUniqueId());
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onSwing(PlayerArmSwingEvent e) {
        if (e.getHand() != EquipmentSlot.HAND) return;
        PlayerCombatant pc = pc(e.getPlayer());
        if (pc == null) return;
        long now = plugin.now();
        // 우클릭과 같은 틱에 들어온 휘두르기는 무시 (아이템 사용 애니메이션)
        if (now - pc.input.lastRightClick <= 0) return;
        pc.input.swing(now);
        if (pc.state == CombatState.EXECUTING) plugin.combat().executionClick(pc, now);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = false)
    public void onInteract(PlayerInteractEvent e) {
        PlayerCombatant pc = pc(e.getPlayer());
        if (pc == null) return;
        e.setCancelled(true);
        if (e.getHand() == EquipmentSlot.OFF_HAND) return;
        if (e.getAction() == Action.RIGHT_CLICK_AIR || e.getAction() == Action.RIGHT_CLICK_BLOCK) {
            long now = plugin.now();
            if (pc.input.rightClick(now)) plugin.combat().secondary(pc, now);
        }
    }

    @EventHandler
    public void onInteractEntity(PlayerInteractEntityEvent e) {
        PlayerCombatant pc = pc(e.getPlayer());
        if (pc == null) return;
        e.setCancelled(true);
        if (e.getHand() != EquipmentSlot.HAND) return;
        long now = plugin.now();
        if (pc.input.rightClick(now)) plugin.combat().secondary(pc, now);
    }

    @EventHandler
    public void onInput(PlayerInputEvent e) {
        PlayerCombatant pc = pc(e.getPlayer());
        if (pc == null) return;
        boolean wasJump = pc.input.jump;
        pc.input.forward = e.getInput().isForward();
        pc.input.backward = e.getInput().isBackward();
        pc.input.left = e.getInput().isLeft();
        pc.input.right = e.getInput().isRight();
        pc.input.sneak = e.getInput().isSneak();
        pc.input.jump = e.getInput().isJump();
        if (pc.input.jump && !wasJump) {
            long now = plugin.now();
            pc.input.lastJumpPress = now;
            plugin.combat().space(pc, now);
        }
    }

    @EventHandler
    public void onSwap(PlayerSwapHandItemsEvent e) {
        PlayerCombatant pc = pc(e.getPlayer());
        if (pc == null) return;
        e.setCancelled(true);
        plugin.masks().onFKey(pc, plugin.now());
    }

    @EventHandler
    public void onHeld(PlayerItemHeldEvent e) {
        if (pc(e.getPlayer()) == null) return;
        e.setCancelled(true);
        e.getPlayer().getInventory().setHeldItemSlot(0);
    }

    @EventHandler
    public void onDrop(PlayerDropItemEvent e) {
        if (pc(e.getPlayer()) != null) e.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.LOW)
    public void onClick(InventoryClickEvent e) {
        if (!(e.getWhoClicked() instanceof Player p)) return;
        PlayerCombatant pc = pc(p);
        if (pc == null) return;
        e.setCancelled(true);
        plugin.masks().onInventoryClick(pc, e);
    }

    @EventHandler
    public void onDrag(InventoryDragEvent e) {
        if (e.getWhoClicked() instanceof Player p && pc(p) != null) e.setCancelled(true);
    }

    @EventHandler
    public void onSprint(PlayerToggleSprintEvent e) {
        if (e.isSprinting() && pc(e.getPlayer()) != null) e.setCancelled(true);
    }

    @EventHandler
    public void onFood(FoodLevelChangeEvent e) {
        if (e.getEntity() instanceof Player p && pc(p) != null) {
            e.setCancelled(true);
            p.setFoodLevel(6);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onDamage(EntityDamageEvent e) {
        Arena a = plugin.arena();
        if (a == null) {
            if (e.getEntity() instanceof Player && plugin.lobby().isLobby(e.getEntity().getWorld())) e.setCancelled(true);
            return;
        }
        // 게임 월드의 바닐라 피해는 모두 무시 (자체 판정 사용). 공허로 떨어진 경우만 처리
        if (e.getEntity().getWorld().equals(a.world)) {
            e.setCancelled(true);
            if (e.getCause() == EntityDamageEvent.DamageCause.VOID) {
                var c = a.byEntity.get(e.getEntity().getUniqueId());
                if (c != null && c.isAlive()) plugin.combat().kill(c, c.lastAttacker, dev.violence.logic.KillType.GUN, new dev.violence.math.Vec3(0, -1, 0), false);
            }
        }
    }

    @EventHandler
    public void onBreak(BlockBreakEvent e) {
        if (plugin.arena() != null && e.getBlock().getWorld().equals(plugin.arena().world)) e.setCancelled(true);
    }

    @EventHandler
    public void onBlockDamage(BlockDamageEvent e) {
        if (plugin.arena() != null && e.getBlock().getWorld().equals(plugin.arena().world)) e.setCancelled(true);
    }

    @EventHandler
    public void onPlace(BlockPlaceEvent e) {
        if (plugin.arena() != null && e.getBlock().getWorld().equals(plugin.arena().world)) e.setCancelled(true);
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        plugin.pack().send(e.getPlayer());
        plugin.lobby().onJoin(e.getPlayer());
        if (plugin.arena() != null) plugin.game().onPlayerJoinMidGame(e.getPlayer());
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        plugin.game().onPlayerQuit(e.getPlayer());
        plugin.shake().remove(e.getPlayer());
        plugin.hud().forget(e.getPlayer().getUniqueId());
    }
}
