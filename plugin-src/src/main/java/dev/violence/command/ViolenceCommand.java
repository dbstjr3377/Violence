package dev.violence.command;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import dev.violence.mask.Mask;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponType;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

/**
 * /violence (별칭 /vio) 관리 명령어.
 * /게임시작, /게임중단 은 Skript 스크립트가 정의하며, Skript 가 없으면 플러그인이 대신 등록한다.
 */
public final class ViolenceCommand implements TabExecutor {
    private final ViolencePlugin plugin;
    private final MapEditor editor;

    public ViolenceCommand(ViolencePlugin plugin) {
        this.plugin = plugin;
        this.editor = new MapEditor(plugin);
    }

    public MapEditor editor() { return editor; }

    private static void msg(CommandSender s, String text) { s.sendMessage(Component.text(text, NamedTextColor.LIGHT_PURPLE)); }

    private static int intArg(String[] a, int i, int def) {
        if (a.length <= i) return def;
        try {
            return Integer.parseInt(a[i]);
        } catch (NumberFormatException e) {
            return def;
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length == 0) {
            help(sender);
            return true;
        }
        String sub = args[0].toLowerCase();
        switch (sub) {
            case "start" -> plugin.game().start(sender, args.length > 1 ? args[1] : null, intArg(args, 2, -1), intArg(args, 3, -1), intArg(args, 4, -1));
            case "stop" -> plugin.game().stop(sender);
            case "cutscene" -> cutscene(sender, args);
            case "award", "combobonus" -> {
                // Skript 콜백: /violence award <플레이어> <점수>
                if (!(sender instanceof ConsoleCommandSender) && !sender.isOp()) return true;
                if (args.length < 3 || plugin.arena() == null) return true;
                Player p = Bukkit.getPlayerExact(args[1]);
                if (p == null) return true;
                PlayerCombatant pc = plugin.arena().players.get(p.getUniqueId());
                if (pc == null) return true;
                int pts = intArg(args, 2, 0);
                if (sub.equals("award")) plugin.game().scores().awardFromSkript(pc, pts);
                else plugin.game().scores().comboBonus(pc, pts);
            }
            case "maps" -> {
                msg(sender, "맵 목록:");
                for (String id : plugin.maps().mapIds()) {
                    sender.sendMessage(Component.text(" - " + id + "  " + plugin.maps().displayName(id)
                            + (plugin.maps().hasSaved(id) ? "" : "  (첫 게임 때 자동 생성)"), NamedTextColor.WHITE));
                }
            }
            case "map" -> mapCommand(sender, args);
            case "give" -> {
                if (!(sender instanceof Player p) || args.length < 2) return true;
                Arena a = plugin.arena();
                PlayerCombatant pc = a == null ? null : a.players.get(p.getUniqueId());
                WeaponType t = plugin.weapons().get(args[1]);
                if (pc == null || t == null) {
                    msg(sender, "게임 중에만 사용 가능 / 무기 id 확인: " + plugin.weapons().all().stream().map(WeaponType::id).collect(Collectors.joining(", ")));
                    return true;
                }
                pc.weapon = t.isFist() ? null : new WeaponInstance(t);
                pc.refreshEquipment();
            }
            case "mask" -> {
                if (!(sender instanceof Player p) || args.length < 2) return true;
                Arena a = plugin.arena();
                PlayerCombatant pc = a == null ? null : a.players.get(p.getUniqueId());
                Mask m = Mask.parse(args[1]);
                if (pc == null || m == null) {
                    msg(sender, "게임 중에만 사용 가능 / 가면: " + java.util.Arrays.stream(Mask.values()).map(Mask::name).collect(Collectors.joining(", ")));
                    return true;
                }
                plugin.masks().equip(pc, m);
            }
            case "offer" -> {
                if (!(sender instanceof Player p) || plugin.arena() == null) return true;
                PlayerCombatant pc = plugin.arena().players.get(p.getUniqueId());
                if (pc != null) plugin.masks().offer(pc);
            }
            case "reloadpack" -> {
                plugin.pack().reload();
                for (Player p : Bukkit.getOnlinePlayers()) plugin.pack().send(p);
                msg(sender, "리소스팩을 다시 보냈습니다.");
            }
            case "info" -> {
                Arena a = plugin.arena();
                msg(sender, "상태: " + plugin.game().state() + (a == null ? "" : "  맵: " + a.map.displayName
                        + "  플레이어 " + a.players.size() + "  NPC " + a.npcs.size() + "  바닥 무기 " + a.groundWeapons.size()
                        + "  문 " + a.doors.size() + "  보행노드 " + a.nav.size() + "  추적 엔티티 " + a.tracked.size()));
                msg(sender, "Skript 연동: " + (plugin.game().bridge().available() ? "사용 중" : "없음 (기본 규칙)"));
            }
            default -> help(sender);
        }
        return true;
    }

    private void mapCommand(CommandSender sender, String[] args) {
        if (args.length < 2) {
            msg(sender, "/vio map <generate|edit|save|close|weapon|spawn|door|bounds>");
            return;
        }
        String op = args[1].toLowerCase();
        if (op.equals("generate")) {
            if (plugin.arena() != null) {
                msg(sender, "게임 중에는 생성할 수 없습니다.");
                return;
            }
            String id = args.length > 2 ? args[2] : "all";
            List<MapGenerator> gens = new ArrayList<>();
            if (id.equals("all")) gens.addAll(Generators.all());
            else if (Generators.get(id) != null) gens.add(Generators.get(id));
            else {
                msg(sender, "알 수 없는 내장 맵: " + id);
                return;
            }
            for (MapGenerator g : gens) {
                World w = plugin.maps().createWorld("vedit");
                long t0 = System.currentTimeMillis();
                var gm = g.generate(new dev.violence.map.WorldBlockAccess(w), new Random(g.id().hashCode() * 31L + 7));
                try {
                    plugin.maps().saveMap(w, gm);
                    var nav = plugin.maps().buildNav(w, gm);
                    msg(sender, g.id() + " 생성 완료: " + (gm.maxX - gm.minX + 1) + "x" + (gm.maxZ - gm.minZ + 1) + "x" + (gm.maxY - gm.minY + 1)
                            + ", 무기지점 " + gm.weaponSpots.size() + ", 리스폰 " + gm.spawns.size() + ", 문 " + gm.doors.size()
                            + ", 보행노드 " + nav.size() + " (" + (System.currentTimeMillis() - t0) + "ms)");
                } catch (IOException e) {
                    msg(sender, g.id() + " 저장 실패: " + e.getMessage());
                }
                plugin.maps().destroy(w);
            }
            return;
        }
        if (!(sender instanceof Player p)) {
            msg(sender, "플레이어만 사용할 수 있습니다.");
            return;
        }
        switch (op) {
            case "edit" -> {
                if (args.length < 3) msg(p, "/vio map edit <맵id>");
                else editor.edit(p, args[2]);
            }
            case "save" -> editor.save(p);
            case "close" -> editor.close();
            case "bounds" -> editor.bounds(p);
            case "weapon" -> {
                if (args.length > 2 && args[2].equalsIgnoreCase("remove")) editor.weaponRemove(p);
                else editor.weaponAdd(p, args.length > 3 ? args[3] : null);
            }
            case "spawn" -> {
                if (args.length > 2 && args[2].equalsIgnoreCase("remove")) editor.spawnRemove(p);
                else editor.spawnAdd(p);
            }
            case "door" -> {
                if (args.length > 2 && args[2].equalsIgnoreCase("remove")) editor.doorRemove(p);
                else editor.doorAdd(p);
            }
            default -> msg(p, "알 수 없는 하위 명령: " + op);
        }
    }

    private void help(CommandSender s) {
        msg(s, "VIOLENCE 명령어");
        s.sendMessage(Component.text(" /게임시작 [맵] [목표킬] [제한시간(초)]  /게임중단", NamedTextColor.WHITE));
        s.sendMessage(Component.text(" /vio start [맵] [NPC수] [목표킬] [초] · stop · maps · info · reloadpack", NamedTextColor.WHITE));
        s.sendMessage(Component.text(" /vio map generate [맵|all] · edit <맵> · weapon add [무기] · weapon remove", NamedTextColor.WHITE));
        s.sendMessage(Component.text("   · spawn add|remove · door add|remove · bounds · save · close", NamedTextColor.WHITE));
        s.sendMessage(Component.text(" /vio give <무기> · mask <가면> · offer (테스트용)", NamedTextColor.WHITE));
    }

    /**
     * 컷씬 (Skript cutscene.sk 가 콘솔로 호출하거나 어드민이 직접 사용)
     *  /violence cutscene begin <어드민>
     *  /violence cutscene say <대상: 플레이어 이름 | UUID | none> <초상화> <대사...>
     *  /violence cutscene next | end
     */
    private void cutscene(CommandSender sender, String[] args) {
        if (!(sender instanceof ConsoleCommandSender) && !sender.hasPermission("violence.admin")) return;
        String op = args.length > 1 ? args[1].toLowerCase() : "";
        switch (op) {
            case "begin" -> {
                Player a = args.length > 2 ? Bukkit.getPlayerExact(args[2]) : (sender instanceof Player p ? p : null);
                plugin.dialog().begin(sender, a);
            }
            case "say" -> {
                if (args.length < 5) {
                    msg(sender, "/violence cutscene say <대상> <초상화> <대사>");
                    return;
                }
                org.bukkit.entity.Entity target = null;
                if (!args[2].equalsIgnoreCase("none")) {
                    target = Bukkit.getPlayerExact(args[2]);
                    if (target == null) {
                        try {
                            target = Bukkit.getEntity(java.util.UUID.fromString(args[2]));
                        } catch (IllegalArgumentException ignored) {
                            // 이름도 UUID 도 아니면 카메라를 옮기지 않음
                        }
                    }
                }
                String text = String.join(" ", java.util.Arrays.copyOfRange(args, 4, args.length));
                plugin.dialog().say(sender, target, args[3], text);
            }
            case "next" -> plugin.dialog().click();
            case "end" -> plugin.dialog().end();
            case "reload" -> {
                plugin.dialog().reloadAssets();
                msg(sender, "cutscene.json 을 다시 읽었습니다.");
            }
            default -> msg(sender, "/violence cutscene <begin|say|next|end|reload>");
        }
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length == 1) return filter(List.of("start", "stop", "cutscene", "maps", "map", "info", "give", "mask", "offer", "reloadpack"), args[0]);
        if (args.length == 2 && args[0].equalsIgnoreCase("start")) return filter(plugin.maps().mapIds(), args[1]);
        if (args.length == 2 && args[0].equalsIgnoreCase("cutscene")) return filter(List.of("begin", "say", "next", "end", "reload"), args[1]);
        if (args.length == 2 && args[0].equalsIgnoreCase("map")) return filter(List.of("generate", "edit", "save", "close", "weapon", "spawn", "door", "bounds"), args[1]);
        if (args.length == 3 && args[0].equalsIgnoreCase("map") && (args[1].equalsIgnoreCase("edit") || args[1].equalsIgnoreCase("generate"))) return filter(plugin.maps().mapIds(), args[2]);
        if (args.length == 2 && args[0].equalsIgnoreCase("give")) return filter(plugin.weapons().all().stream().map(WeaponType::id).toList(), args[1]);
        if (args.length == 2 && args[0].equalsIgnoreCase("mask")) return filter(java.util.Arrays.stream(Mask.values()).map(Mask::name).toList(), args[1]);
        return List.of();
    }

    private static List<String> filter(List<String> in, String prefix) {
        return in.stream().filter(s -> s.toLowerCase().startsWith(prefix.toLowerCase())).toList();
    }
}
