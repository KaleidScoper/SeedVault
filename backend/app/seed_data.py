"""
Seed data for development and testing.
Covers all variable dimensions: editions, versions, world types, mod_env, tags, statuses.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    User, Seed, Screenshot, KeyCoord, Tag, SeedTag, Like,
    Version, Collection, CollectionSeed, Comment, Notification,
)


async def seed_all(db: AsyncSession):
    # Check if already seeded
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return

    now = datetime.utcnow()

    # ═══ Users ═══
    admin = User(
        display_name="Kaleid_5coper",
        minecraft_uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        minecraft_username="Kaleid_5coper",
        owns_java_edition=True,
        role="admin",
        email="admin@seedvault.dev",
    )
    player2 = User(
        display_name="方块猎人",
        minecraft_uuid="11111111-2222-3333-4444-555555555555",
        minecraft_username="BlockHunter",
        owns_java_edition=True,
    )
    player3 = User(
        display_name="建筑大师",
        minecraft_username="BuilderPro",
        owns_java_edition=False,
    )
    player4 = User(
        display_name="速通玩家",
        minecraft_uuid="66666666-7777-8888-9999-aaaaaaaaaaaa",
        minecraft_username="SpeedRunner",
        owns_java_edition=True,
    )
    db.add_all([admin, player2, player3, player4])
    await db.flush()

    # ═══ Tags ═══
    tag_data = [
        # gameplay
        ("survival", "生存向", "🏕️", "gameplay"),
        ("speedrun", "速通向", "⚔️", "gameplay"),
        ("building", "建筑向", "🏗️", "gameplay"),
        ("hardcore", "极限模式", "💀", "gameplay"),
        ("challenge", "挑战向", "🎯", "gameplay"),
        # feature
        ("spawn_wonder", "出生点奇观", "🌄", "feature"),
        ("rare_biome", "稀有群系", "🍄", "feature"),
        ("terrain", "地形奇观", "🏔️", "feature"),
        ("village", "近出生点村庄", "🏘️", "feature"),
        ("stronghold", "近出生点要塞", "🏰", "feature"),
        ("ancient_city", "古代城市", "🏛️", "feature"),
        ("trial_chamber", "试炼室集群", "⚗️", "feature"),
        ("diamond", "资源富集", "💎", "feature"),
        ("island", "孤岛生存", "🌊", "feature"),
        # special (system-managed)
        ("verified", "已验证", "✅", "special"),
        ("hot", "热门", "🔥", "special"),
        ("new", "新版本", "🆕", "special"),
    ]
    tag_objs = {}
    for key, label, icon, cat in tag_data:
        t = Tag(key=key, label=label, icon=icon, category=cat)
        db.add(t)
        tag_objs[key] = t
    await db.flush()

    # ═══ Versions ═══
    ver_data = [
        ("java", "1.21.5", True, 100),
        ("java", "1.21.4", False, 99),
        ("java", "1.21.1", False, 98),
        ("java", "1.20.6", False, 97),
        ("java", "1.20.1", False, 96),
        ("bedrock", "1.21.70", True, 100),
        ("bedrock", "1.21.60", False, 99),
        ("bedrock", "1.21.50", False, 98),
    ]
    for ed, ver, latest, order in ver_data:
        db.add(Version(edition=ed, version=ver, is_latest=latest, sort_order=order))
    await db.flush()

    # ═══ Placeholder screenshot helper ═══
    def make_screenshots(uploader_id: int, *descriptions: str) -> list[Screenshot]:
        screenshots = []
        for i, desc in enumerate(descriptions):
            filename = f"seed_{uploader_id}_{i+1}.webp"
            # Create placeholder .txt
            import os
            txt_path = os.path.join("uploads", "screenshots", filename + ".txt")
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, "w") as f:
                f.write(desc)
            ss = Screenshot(
                uploader_id=uploader_id,
                file_path=f"screenshots/{filename}",
                is_cover=(i == 0),
                sort_order=i,
                status="active",
            )
            screenshots.append(ss)
        return screenshots

    # ═══ Seeds ═══
    seeds_data = [
        # --- Java approved seeds ---
        {
            "title": "出生点下方古代城市",
            "description": "出生点正下方 Y=-30 处就是一座完整的古代城市，附带末地传送门。适合速通和建筑向玩家。\n\n关键坐标：古城入口 X:120 Z:64，末地传送门 X:800 Z:32。已实测 1.21.4 和 1.21.5 均可用。",
            "seed_value": "123456789",
            "edition": "java",
            "tested_version": "1.21.4",
            "compatible_range": "1.21.4 ~ 1.21.5",
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 0, "spawn_z": 64,
            "status": "approved",
            "uploader_id": admin.id,
            "like_count": 42, "collection_count": 3, "view_count": 1234,
            "created_at": now - timedelta(days=5),
            "approved_at": now - timedelta(days=4),
            "approved_by": admin.id,
            "tags": ["survival", "speedrun", "ancient_city", "stronghold"],
            "coords": [
                ("古代城市入口", 120, -30, 64),
                ("末地传送门", 800, None, 32),
            ],
            "screenshots": [
                ("16:9 Minecraft screenshot showing spawn point in a plains biome at sunrise. The landscape is flat with scattered oak trees. Coordinates overlay shows X:0 Z:64.",),
                ("Overhead view looking down into a massive ancient city in a deep dark biome. Sculk blocks cover the structures. The city spreads across the entire visible area underground at Y=-30.",),
                ("The end portal room inside the stronghold. Stone bricks and silverfish spawner visible. Coordinates X:800 Z:32 labeled on screen.",),
            ],
        },
        {
            "title": "蘑菇岛出生点",
            "description": "出生在一座巨大的蘑菇岛上，四周环海。岛上没有敌对生物，非常适合生存建造。附近有海底神殿。",
            "seed_value": "-8765432109876543210",
            "edition": "java",
            "tested_version": "1.21.5",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 16, "spawn_z": -128,
            "status": "approved",
            "uploader_id": player2.id,
            "like_count": 28, "collection_count": 5, "view_count": 890,
            "created_at": now - timedelta(days=10),
            "approved_at": now - timedelta(days=9),
            "approved_by": admin.id,
            "tags": ["survival", "building", "rare_biome", "spawn_wonder"],
            "coords": [
                ("海底神殿", 320, 62, -200),
                ("巨型蘑菇", 50, 80, -100),
            ],
            "screenshots": [
                ("Aerial view of a massive mushroom island biome. Giant red and brown mushrooms covering rolling hills. The mycelium ground is gray-purple. Ocean surrounds the island on all sides.",),
                ("Player standing next to a giant red mushroom on the island shoreline. Ocean monument visible in the distance. Bright daylight, clear sky.",),
            ],
        },
        {
            "title": "村庄包围的试炼室",
            "description": "三个村庄围绕一座试炼室，出生即可交易和挑战。平原群系，资源丰富。每个村庄都有铁匠铺。",
            "seed_value": "555666777",
            "edition": "java",
            "tested_version": "1.21.5",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 0, "spawn_z": 0,
            "status": "approved",
            "uploader_id": player4.id,
            "like_count": 67, "collection_count": 12, "view_count": 2300,
            "created_at": now - timedelta(days=1),
            "approved_at": now - timedelta(hours=12),
            "approved_by": admin.id,
            "tags": ["survival", "challenge", "village", "trial_chamber", "diamond"],
            "coords": [
                ("村庄 A（铁匠铺）", -96, 65, 128),
                ("村庄 B（图书馆）", 200, 64, -80),
                ("村庄 C", 350, 63, 300),
                ("试炼室", 0, 30, 0),
            ],
            "screenshots": [
                ("Panoramic view from a hilltop showing three villages spread across a plains biome. Wheat fields between them. A trial chamber structure partially visible underground at the center.",),
                ("Interior of the trial chamber. Multiple trial spawners visible with ominous trials active. Player in iron armor fighting breezes.",),
                ("Village A blacksmith chest contents: 3 diamonds, 5 iron ingots, obsidian. Inventory screen focused on the loot.",),
                ("Map view showing the triangular layout of villages around the central trial chamber. Each village marked with banners.",),
            ],
        },
        # --- Java approved seed (large biomes) ---
        {
            "title": "巨型针叶林生存",
            "description": "大型群系模式下的巨型针叶林，出生点即有一片巨型云杉。适合喜欢雪地建筑的玩家。",
            "seed_value": "111222333444555",
            "edition": "java",
            "tested_version": "1.20.6",
            "compatible_range": None,
            "world_type": "large_biomes",
            "mod_env": "vanilla",
            "spawn_x": 50, "spawn_z": 200,
            "status": "approved",
            "uploader_id": player3.id,
            "like_count": 15, "collection_count": 2, "view_count": 450,
            "created_at": now - timedelta(days=20),
            "approved_at": now - timedelta(days=19),
            "approved_by": admin.id,
            "tags": ["survival", "building", "terrain"],
            "coords": [
                ("云杉村庄", 300, 68, 400),
            ],
            "screenshots": [
                ("Dense giant tree taiga biome. Massive 2x2 spruce trees towering overhead. Snow on the ground. Podzol visible. A cozy feel with lantern light from a small player-built cabin.",),
            ],
        },
        # --- Java approved seed (modpack) ---
        {
            "title": "Terralith 奇幻地形",
            "description": "在 Terralith 2.5.x 模组下生成的绝美地形。出生点位于悬崖边，俯瞰壮丽的峡谷。必须安装 Terralith 模组才能复现。",
            "seed_value": "terralith_dream_2026",
            "edition": "java",
            "tested_version": "1.20.1",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "modpack",
            "modpack_name": "Terralith 2.5.4",
            "modpack_version": "2.5.4",
            "spawn_x": -400, "spawn_z": 600,
            "status": "approved",
            "uploader_id": player2.id,
            "like_count": 31, "collection_count": 4, "view_count": 780,
            "created_at": now - timedelta(days=15),
            "approved_at": now - timedelta(days=14),
            "approved_by": admin.id,
            "tags": ["building", "terrain", "spawn_wonder"],
            "coords": [
                ("峡谷观景点", -400, 120, 600),
                ("樱花林", -200, 75, 800),
            ],
            "screenshots": [
                ("Stunning Terralith-generated landscape. A dramatic cliff edge at spawn overlooks a deep canyon with layered rock strata. Cherry blossom trees at the canyon rim. Golden hour lighting.",),
                ("The canyon floor showing custom Terralith rock formations and a winding river. Lush vegetation in multiple colors.",),
            ],
        },
        # --- Java approved seed (NeoForge) ---
        {
            "title": "NeoForge 测试种子",
            "description": "在纯 NeoForge（无任何世界生成 mod）环境下测试的种子。出生点附近有繁花森林和蜂巢。提交者注：在 NeoForge 47.3.0 测试。",
            "seed_value": "987654321",
            "edition": "java",
            "tested_version": "1.21.1",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "neoforge",
            "spawn_x": -50, "spawn_z": 30,
            "status": "approved",
            "uploader_id": player4.id,
            "like_count": 3, "collection_count": 0, "view_count": 120,
            "created_at": now - timedelta(days=30),
            "approved_at": now - timedelta(days=29),
            "approved_by": admin.id,
            "tags": ["survival", "spawn_wonder"],
            "coords": [
                ("繁花森林", -50, 64, 30),
            ],
            "screenshots": [
                ("Flower forest biome at spawn. Multiple types of flowers covering the ground. Bee hives on several oak and birch trees. Clear blue sky. NeoForge version watermark in corner.",),
            ],
        },
        # --- Bedrock approved seeds ---
        {
            "title": "基岩版孤岛挑战",
            "description": "基岩版 1.21.60 测试。出生在一座小岛上，只有一棵树。经典孤岛生存开局，脚下就是废弃矿井。",
            "seed_value": "42069",
            "edition": "bedrock",
            "tested_version": "1.21.60",
            "compatible_range": "1.21.60 ~ 1.21.70",
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 8, "spawn_z": 8,
            "status": "approved",
            "uploader_id": admin.id,
            "like_count": 89, "collection_count": 20, "view_count": 3400,
            "created_at": now - timedelta(days=2),
            "approved_at": now - timedelta(days=1),
            "approved_by": admin.id,
            "tags": ["survival", "challenge", "island", "diamond"],
            "coords": [
                ("废弃矿井入口（水下）", 10, 45, 10),
                ("沉船", 120, 55, -80),
            ],
            "screenshots": [
                ("Tiny island in the middle of deep ocean. One oak tree. A player standing on the sand shore. The island is about 20x20 blocks. Sunset colors on the horizon.",),
                ("Underwater view showing the entrance to an abandoned mineshaft directly below the island. Wooden planks and rails visible. Bubbles from player respiration.",),
                ("A shipwreck nearby, partially above water, hull intact. Coordinates X:120 Z:-80.",),
            ],
        },
        {
            "title": "基岩版村庄集群",
            "description": "出生点 500 格内有 6 个村庄。平原、沙漠、雪地村庄各两个。基岩版 1.21.70 最新版测试。",
            "seed_value": "bedrock_village_hub",
            "edition": "bedrock",
            "tested_version": "1.21.70",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 100, "spawn_z": -50,
            "status": "approved",
            "uploader_id": player3.id,
            "like_count": 22, "collection_count": 3, "view_count": 670,
            "created_at": now - timedelta(days=8),
            "approved_at": now - timedelta(days=7),
            "approved_by": admin.id,
            "tags": ["survival", "village", "diamond"],
            "coords": [
                ("沙漠村庄 1", 200, 65, -50),
                ("平原村庄 1", 100, 63, 200),
                ("雪地村庄 1", -150, 68, -100),
            ],
            "screenshots": [
                ("Aerial shot showing three distinct village types near each other: desert village with sandstone, plains village with oak, snowy village with spruce. Rare multi-biome convergence.",),
            ],
        },
        # --- Bedrock superflat ---
        {
            "title": "超平坦红石实验室",
            "description": "基岩版超平坦世界，适合红石测试和建筑。预设为红石 Ready。",
            "seed_value": "redstone_lab_001",
            "edition": "bedrock",
            "tested_version": "1.21.60",
            "compatible_range": None,
            "world_type": "superflat",
            "mod_env": "vanilla",
            "spawn_x": 0, "spawn_z": 0,
            "status": "approved",
            "uploader_id": player2.id,
            "like_count": 8, "collection_count": 1, "view_count": 300,
            "created_at": now - timedelta(days=25),
            "approved_at": now - timedelta(days=24),
            "approved_by": admin.id,
            "tags": ["building", "challenge"],
            "coords": [
                ("史莱姆区块", 16, 4, 16),
            ],
            "screenshots": [
                ("Flat superflat world at Y=4. Green grass as far as the eye can see. Slimes bouncing in the distance. A complex redstone door mechanism built at spawn.",),
            ],
        },
        # --- Java pending seed ---
        {
            "title": "待审核：苍白花园开局",
            "description": "1.21.5 新版苍白花园群系，出生点就在苍白橡树旁边。",
            "seed_value": "pale_garden_test",
            "edition": "java",
            "tested_version": "1.21.5",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": -20, "spawn_z": 40,
            "status": "pending",
            "uploader_id": player3.id,
            "like_count": 0, "collection_count": 0, "view_count": 0,
            "created_at": now - timedelta(hours=3),
            "tags": ["survival", "rare_biome", "spawn_wonder"],
            "coords": [
                ("苍白橡树", -20, 64, 40),
            ],
            "screenshots": [
                ("Pale garden biome at night. Pale oak trees with hanging moss. The grey-green foliage is eerie. A creaking heart visible on one tree trunk. Pale oak wood planks in inventory.",),
            ],
        },
        # --- Java rejected seed ---
        {
            "title": "（被拒绝）虚假古代城市",
            "description": "投稿者声称出生点有古代城市，实际截图不匹配。已拒绝。",
            "seed_value": "fake_city_999",
            "edition": "java",
            "tested_version": "1.21.4",
            "compatible_range": None,
            "world_type": "normal",
            "mod_env": "vanilla",
            "spawn_x": 0, "spawn_z": 0,
            "status": "rejected",
            "uploader_id": player3.id,
            "rejection_reason": "截图与描述不符，出生点附近无古代城市",
            "like_count": 0, "collection_count": 0, "view_count": 0,
            "created_at": now - timedelta(days=40),
            "approved_at": now - timedelta(days=39),
            "approved_by": admin.id,
            "tags": ["survival"],
            "coords": [],
            "screenshots": [
                ("Plain plains biome at spawn. No structures visible. Misleading submission - does not match description of ancient city.",),
            ],
        },
    ]

    all_seeds = []
    for i, sd in enumerate(seeds_data):
        seed_numeric = None
        try:
            seed_numeric = int(sd["seed_value"])
            if seed_numeric > 2**63 - 1 or seed_numeric < -(2**63):
                seed_numeric = None
        except (ValueError, OverflowError):
            seed_numeric = None

        seed = Seed(
            title=sd["title"],
            description=sd["description"],
            seed_value=sd["seed_value"],
            seed_numeric=seed_numeric,
            edition=sd["edition"],
            tested_version=sd["tested_version"],
            compatible_range=sd.get("compatible_range"),
            world_type=sd["world_type"],
            mod_env=sd["mod_env"],
            modpack_name=sd.get("modpack_name"),
            modpack_version=sd.get("modpack_version"),
            spawn_x=sd["spawn_x"],
            spawn_z=sd["spawn_z"],
            status=sd["status"],
            rejection_reason=sd.get("rejection_reason"),
            uploader_id=sd["uploader_id"],
            like_count=sd["like_count"],
            collection_count=sd["collection_count"],
            view_count=sd["view_count"],
            created_at=sd["created_at"],
            approved_at=sd.get("approved_at"),
            approved_by=sd.get("approved_by"),
        )
        db.add(seed)
        await db.flush()
        all_seeds.append(seed)

        # Screenshots
        for j, (desc,) in enumerate(sd.get("screenshots", [])):
            filename = f"seed_{seed.id}_{j+1}.webp"
            import os
            txt_path = os.path.join("uploads", "screenshots", filename + ".txt")
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, "w") as f:
                f.write(desc)
            db.add(Screenshot(
                seed_id=seed.id,
                uploader_id=sd["uploader_id"],
                file_path=f"screenshots/{filename}",
                is_cover=(j == 0),
                sort_order=j,
                status="active",
            ))

        # Tags
        for tag_key in sd["tags"]:
            tag = tag_objs.get(tag_key)
            if tag:
                db.add(SeedTag(seed_id=seed.id, tag_id=tag.id))

        # Key coords
        for label, x, y, z in sd["coords"]:
            db.add(KeyCoord(seed_id=seed.id, label=label, x=x, y=y, z=z))

    await db.flush()

    # ═══ Likes ═══
    # Admin likes some seeds
    for seed_idx in [0, 1, 2, 6, 7]:
        db.add(Like(user_id=admin.id, seed_id=all_seeds[seed_idx].id,
                     created_at=now - timedelta(days=3)))
    # Player2 likes seeds
    for seed_idx in [0, 2, 4, 5, 6]:
        db.add(Like(user_id=player2.id, seed_id=all_seeds[seed_idx].id,
                     created_at=now - timedelta(days=2)))
    # Player4 speedrunner likes survival/speedrun seeds
    for seed_idx in [0, 2, 3, 6, 7]:
        db.add(Like(user_id=player4.id, seed_id=all_seeds[seed_idx].id,
                     created_at=now - timedelta(days=1)))

    await db.flush()

    # ═══ Collections ═══
    coll1 = Collection(
        user_id=admin.id,
        name="1.21.4 生存好种",
        description="适合开新档的种子",
        is_public=True,
    )
    coll2 = Collection(
        user_id=player2.id,
        name="建筑灵感",
        description="地形和村庄都很漂亮的种子",
        is_public=True,
    )
    coll3 = Collection(
        user_id=player4.id,
        name="速通练习",
        description="速通向种子合集",
        is_public=False,
    )
    db.add_all([coll1, coll2, coll3])
    await db.flush()

    # Add seeds to collections
    for seed_idx in [0, 1, 2, 6, 7]:
        db.add(CollectionSeed(collection_id=coll1.id, seed_id=all_seeds[seed_idx].id))
    for seed_idx in [1, 4, 7]:
        db.add(CollectionSeed(collection_id=coll2.id, seed_id=all_seeds[seed_idx].id))
    for seed_idx in [0, 2, 6]:
        db.add(CollectionSeed(collection_id=coll3.id, seed_id=all_seeds[seed_idx].id))

    await db.flush()

    # ═══ Comments ═══
    comments_data = [
        (all_seeds[0].id, admin.id, "实测可用！古城就在出生点正下方，太方便了。"),
        (all_seeds[0].id, player2.id, "末地传送门也近，速通党狂喜。"),
        (all_seeds[0].id, player4.id, "1.21.5 也完美复现，已验证。"),
        (all_seeds[6].id, admin.id, "基岩版难得的孤岛好种，废弃矿井就在脚下。"),
        (all_seeds[6].id, player3.id, "沉船里有藏宝图，挖到了 8 个钻石 💎"),
        (all_seeds[1].id, player2.id, "蘑菇岛生存太舒服了，没有怪物。"),
        (all_seeds[2].id, player4.id, "三个村庄的试炼室种子，铁匠铺好东西太多了。"),
        (all_seeds[2].id, admin.id, "已加精，欢迎更多 1.21.5 种子投稿。"),
    ]
    for seed_id, author_id, content in comments_data:
        db.add(Comment(
            seed_id=seed_id,
            author_id=author_id,
            content=content,
            created_at=now - timedelta(hours=len(comments_data)),
        ))

    # ═══ Notifications ═══
    db.add(Notification(
        user_id=admin.id,
        type="seed_approved",
        message="您的投稿「出生点下方古代城市」已通过审核",
        seed_id=all_seeds[0].id,
    ))

    await db.commit()
    print(f"✅ Seed data loaded: {len(all_seeds)} seeds across all variations")
