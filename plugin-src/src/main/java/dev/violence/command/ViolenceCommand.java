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

    private static void msg(CommandSender s, String text) { dev.violence.chat.NoChat.tell(s, Component.text(text, NamedTextColor.LIGHT_PURPLE)); }

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
            case "as" -> {
                // 관리자/콘솔: /vio as <플레이어> <명령...> = 그 플레이어가 친 것처럼 (테스트 자동화용)
                if (!(sender instanceof ConsoleCommandSender) && !sender.isOp()) return true;
                Player target = args.length > 2 ? Bukkit.getPlayerExact(args[1]) : null;
                if (target == null) {
                    msg(sender, "사용법: /vio as <플레이어> <명령...>");
                    return true;
                }
                return onCommand(target, command, label, java.util.Arrays.copyOfRange(args, 2, args.length));
            }
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
                    dev.violence.chat.NoChat.tell(sender, Component.text(" - " + id + "  " + plugin.maps().displayName(id)
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
            case "test" -> {
                // 테스트용 (관리자): /vio test down = 가장 가까운 NPC 를 내 앞 1.2칸에 데려와 쓰러뜨림 → Space 로 처형 확인
                if (sender instanceof Player fp && args.length > 1 && args[1].equalsIgnoreCase("flash")) {
                    plugin.hud().killFlash(fp);   // 처치 회색 깜빡임만 확인
                    return true;
                }
                if (sender instanceof Player sp && args.length > 2 && args[1].equalsIgnoreCase("skin")) {
                    // /vio test skin <파일>: 플러그인 폴더의 PNG 를 내 1인칭 팔 스킨으로 (오프라인 서버 확인용)
                    java.io.File f = new java.io.File(plugin.getDataFolder(), args[2]);
                    if (!f.isFile()) {
                        msg(sender, "파일 없음: " + f);
                        return true;
                    }
                    plugin.pack().sendSkin(sp, f);
                    msg(sender, "스킨 팩을 보냅니다: " + f.getName());
                    return true;
                }
                if (!(sender instanceof Player p) || plugin.arena() == null) return true;
                Arena a = plugin.arena();
                PlayerCombatant pc = a.players.get(p.getUniqueId());
                if (pc == null) return true;
                if (args.length > 1 && args[1].equalsIgnoreCase("weapon")) {
                    // 가장 가까운 바닥 무기를 1.6칸 앞에서 내려다봄 → 테두리와 정보 카드 확인
                    dev.violence.arena.GroundWeapon g = null;
                    double gd = Double.MAX_VALUE;
                    for (dev.violence.arena.GroundWeapon w : a.groundWeapons) {
                        double d = w.pos.distanceSq(pc.feet());
                        if (d < gd) {
                            gd = d;
                            g = w;
                        }
                    }
                    if (g == null) {
                        msg(sender, "바닥 무기가 없습니다.");
                        return true;
                    }
                    dev.violence.math.Vec3 back = pc.look().horizontal().normalize().mul(-1.6);
                    dev.violence.math.Vec3 at = g.pos.add(back.x(), 0, back.z());
                    dev.violence.math.Vec3 dir = g.pos.add(0, 0.15, 0).sub(at.add(0, 1.62, 0)).normalize();
                    org.bukkit.Location to = new org.bukkit.Location(a.world, at.x(), at.y(), at.z(), (float) dir.yaw(), (float) dir.pitch());
                    p.teleport(to);
                    msg(sender, g.weapon.type().displayName() + " 을(를) 봅니다.");
                    return true;
                }
                if (args.length > 1 && args[1].equalsIgnoreCase("wall")) {
                    // /vio test wall: 바라보는 쪽 벽 앞에 가장 가까운 NPC 를 벽을 등지고 세우고(3초 멈춤), 나는 그 앞 1.6칸에서 바라봄
                    // → 주먹으로 치면 벽에 기대 기절 (벽 처형·벽 시체 촬영용)
                    dev.violence.math.Vec3 f = pc.look().horizontal().normalize();
                    org.bukkit.Location eye = p.getEyeLocation();
                    org.bukkit.util.RayTraceResult r = a.world.rayTraceBlocks(eye, new org.bukkit.util.Vector(f.x(), 0, f.z()), 16,
                            org.bukkit.FluidCollisionMode.NEVER, true);
                    if (r == null) {
                        msg(sender, "앞에 벽이 없습니다.");
                        return true;
                    }
                    org.bukkit.util.Vector hp = r.getHitPosition();
                    dev.violence.math.Vec3 foot = new dev.violence.math.Vec3(hp.getX(), p.getLocation().getY(), hp.getZ());
                    dev.violence.math.Vec3 npcAt = foot.sub(f.mul(0.75));
                    dev.violence.math.Vec3 meAt = npcAt.sub(f.mul(1.6));
                    dev.violence.npc.NpcCombatant near = null;
                    double nd = Double.MAX_VALUE;
                    for (dev.violence.npc.NpcCombatant n : a.npcs) {
                        if (n.state != dev.violence.combat.CombatState.ALIVE || n.execution != null) continue;
                        double d = n.feet().distanceSq(pc.feet());
                        if (d < nd) {
                            nd = d;
                            near = n;
                        }
                    }
                    if (near == null) {
                        msg(sender, "세울 NPC 가 없습니다.");
                        return true;
                    }
                    float yaw = (float) f.yaw();
                    near.teleport(new org.bukkit.Location(a.world, npcAt.x(), npcAt.y(), npcAt.z(), yaw + 180, 0));
                    near.actionLockUntil = plugin.now() + 60;
                    near.moveLockUntil = plugin.now() + 60;
                    p.teleport(new org.bukkit.Location(a.world, meAt.x(), meAt.y(), meAt.z(), yaw, 12));
                    msg(sender, near.name() + " 를 벽 앞에 세웠습니다.");
                    return true;
                }
                if (args.length > 1 && args[1].equalsIgnoreCase("line")) {
                    // /vio test line [n]: 살아 있는 NPC n 명을 앞 5~7칸에 옆으로 늘어세우고 6초 동안 멈춤 (연사 촬영용)
                    int n = args.length > 2 ? Math.max(1, Math.min(8, Integer.parseInt(args[2]))) : 4;
                    dev.violence.math.Vec3 f = pc.look().horizontal().normalize();
                    dev.violence.math.Vec3 rt = new dev.violence.math.Vec3(-f.z(), 0, f.x());
                    int k = 0;
                    for (dev.violence.npc.NpcCombatant npc : a.npcs) {
                        if (k >= n) break;
                        if (npc.state != dev.violence.combat.CombatState.ALIVE || npc.execution != null) continue;
                        // 좁은 복도에서도 벽에 묻히지 않게: 앞쪽으로 1.6칸 간격, 좌우로 조금씩 엇갈림
                        // "col": 한 줄로 (조준을 옮기지 않고 연사로 차례로 쓰러뜨리기), 아니면 좌우로 조금씩 엇갈림
                        boolean col = args.length > 3 && args[3].equalsIgnoreCase("col");
                        double side = col ? 0 : (k % 2 == 0 ? -0.55 : 0.55);
                        dev.violence.math.Vec3 at = pc.feet().add(f.mul(4.0 + k * 1.6)).add(rt.mul(side));
                        org.bukkit.Location l = new org.bukkit.Location(a.world, at.x(), at.y(), at.z(), p.getLocation().getYaw() + 180, 0);
                        npc.teleport(l);
                        npc.actionLockUntil = plugin.now() + 120;
                        npc.moveLockUntil = plugin.now() + 120;
                        k++;
                    }
                    msg(sender, k + " 명을 앞에 세웠습니다.");
                    return true;
                }
                boolean aim = args.length > 1 && args[1].equalsIgnoreCase("aim");
                boolean near = args.length > 1 && args[1].equalsIgnoreCase("near");
                dev.violence.npc.NpcCombatant best = null;
                double bd = Double.MAX_VALUE;
                for (dev.violence.npc.NpcCombatant n : a.npcs) {
                    if (aim ? n.state == dev.violence.combat.CombatState.DEAD : (n.state != dev.violence.combat.CombatState.ALIVE || n.execution != null)) continue;
                    double d = n.feet().distanceSq(pc.feet());
                    if (near && n.weapon != null && n.weapon.type().isGun()) d += 1e6;   // 총 든 NPC 는 나중에
                    if (d < bd) {
                        bd = d;
                        best = n;
                    }
                }
                if (best == null) {
                    msg(sender, "쓰러뜨릴 NPC 가 없습니다.");
                    return true;
                }
                if (aim) {
                    // 가장 가까운 NPC 의 가슴(쓰러져 있으면 몸)을 바라봄 (자리는 그대로, 시선만)
                    dev.violence.math.Vec3 tgt = best.state.isDownedLike() ? best.feet().add(0, 0.2, 0) : best.feet().add(0, 1.2 * best.scale(), 0);
                    dev.violence.math.Vec3 d = tgt.sub(pc.eye()).normalize();
                    org.bukkit.Location me = p.getLocation().clone();
                    me.setYaw((float) d.yaw());
                    me.setPitch((float) d.pitch());
                    p.teleport(me);
                    return true;
                }
                dev.violence.math.Vec3 dir = pc.look().horizontal().normalize();
                if (near) {
                    // 가장 가까운 NPC 를 3칸 앞에 나를 보게 세움 (쓰러뜨리지 않음) → 직접 싸워서 확인
                    org.bukkit.Location l = p.getLocation().clone().add(dir.x() * 3, 0, dir.z() * 3);
                    l.setYaw(p.getLocation().getYaw() + 180);
                    l.setPitch(0);
                    best.teleport(l);
                    best.actionLockUntil = plugin.now() + 60;   // 3초 동안 공격하지 않음 (촬영용)
                    org.bukkit.Location me = p.getLocation().clone();
                    me.setPitch(5);
                    if (args.length > 2) {
                        // /vio test near <무기>: 무기를 쥐고, NPC 는 3초 동안 제자리 (촬영용), 가슴을 겨눔
                        WeaponType wt = plugin.weapons().get(args[2]);
                        if (wt != null) {
                            pc.weapon = wt.isFist() ? null : new WeaponInstance(wt);
                            pc.refreshEquipment();
                        }
                        best.moveLockUntil = plugin.now() + 60;
                        dev.violence.math.Vec3 d = best.feet().add(0, 1.2 * best.scale(), 0).sub(pc.eye()).normalize();
                        me.setYaw((float) d.yaw());
                        me.setPitch((float) d.pitch());
                    }
                    p.teleport(me);
                    msg(sender, best.name() + " 를 앞에 세웠습니다.");
                    return true;
                }
                org.bukkit.Location l = p.getLocation().clone().add(dir.x() * 1.2, 0, dir.z() * 1.2);
                l.setYaw(p.getLocation().getYaw() + 180);
                l.setPitch(0);
                best.teleport(l);
                plugin.combat().knockdown(best, dir, pc, true);
                // 밀려난 뒤 처형할 수 있는 거리(발 앞 0.8칸)로 내가 다가감
                final dev.violence.npc.NpcCombatant target = best;
                if (args.length > 1 && args[1].equalsIgnoreCase("stay")) return true;   // /vio test down stay: 제자리에서 넘어지는 것만 봄
                plugin.later(10, () -> {
                    if (!p.isOnline() || target.state != dev.violence.combat.CombatState.DOWNED) return;
                    org.bukkit.Location to = p.getLocation().clone();
                    to.setX(target.feet().x() - dir.x() * 0.8);
                    to.setZ(target.feet().z() - dir.z() * 0.8);
                    to.setPitch(35);
                    p.teleport(to);
                });
                msg(sender, best.name() + " 를 쓰러뜨렸습니다. Space 로 처형하세요.");
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
        dev.violence.chat.NoChat.tell(s, Component.text(" /게임시작 [맵] [목표킬] [제한시간(초)]  /게임중단", NamedTextColor.WHITE));
        dev.violence.chat.NoChat.tell(s, Component.text(" /vio start [맵] [NPC수] [목표킬] [초] · stop · maps · info · reloadpack", NamedTextColor.WHITE));
        dev.violence.chat.NoChat.tell(s, Component.text(" /vio map generate [맵|all] · edit <맵> · weapon add [무기] · weapon remove", NamedTextColor.WHITE));
        dev.violence.chat.NoChat.tell(s, Component.text("   · spawn add|remove · door add|remove · bounds · save · close", NamedTextColor.WHITE));
        dev.violence.chat.NoChat.tell(s, Component.text(" /vio give <무기> · mask <가면> · offer (테스트용)", NamedTextColor.WHITE));
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
                if (args[2].toLowerCase().startsWith("actor:")) {
                    target = plugin.dialog().actorEntity(args[2].substring(6));
                } else if (!args[2].equalsIgnoreCase("none")) {
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
            case "actor" -> {
                // /violence cutscene actor <이름> <가면|none> <앞> <오른쪽> <바라보는 각도>
                if (args.length < 7) {
                    msg(sender, "/violence cutscene actor <이름> <가면|none> <앞> <오른쪽> <각도>");
                    return;
                }
                try {
                    plugin.dialog().actor(sender, args[2], args[3], Double.parseDouble(args[4]), Double.parseDouble(args[5]), Double.parseDouble(args[6]));
                } catch (NumberFormatException e) {
                    msg(sender, "숫자를 확인하세요: " + e.getMessage());
                }
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
        if (args.length == 1) return filter(List.of("start", "stop", "cutscene", "maps", "map", "info", "give", "mask", "offer", "reloadpack", "test"), args[0]);
        if (args.length == 2 && args[0].equalsIgnoreCase("start")) return filter(plugin.maps().mapIds(), args[1]);
        if (args.length == 2 && args[0].equalsIgnoreCase("cutscene")) return filter(List.of("begin", "say", "actor", "next", "end", "reload"), args[1]);
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
