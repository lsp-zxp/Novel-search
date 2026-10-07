from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "seed_data"
TZ = timezone(timedelta(hours=8))


NOVEL_SPECS = [
    ("雾港来信", "悬疑", "失踪记者留下十二封延迟寄出的信，实习编辑循着邮戳追查一座港城的旧案。"),
    ("星河修理铺", "科幻", "空间站底层修理师偶然获得一台能读取飞船记忆的旧终端。"),
    ("长安无名客", "历史", "安史之乱前夕，一名无籍少年被卷入长安城的密探网络。"),
    ("春山照旧", "古代言情", "女医回到故乡重建药堂，却发现十年前的疫案另有隐情。"),
    ("第七码头", "都市", "深夜代驾司机在第七码头接到一位不存在于订单中的乘客。"),
    ("月落机械城", "科幻", "机械城停止自转后，少女工程师必须在永夜降临前修复城市核心。"),
    ("剑鸣之后", "仙侠", "铸剑学徒能听见兵器遗愿，却唯独听不懂师父留下的断剑。"),
    ("我在妖市开茶馆", "奇幻", "人类茶师在妖怪集市经营茶馆，用一杯茶交换客人的秘密。"),
    ("纸上迷城", "悬疑", "地图绘制员发现自己画出的虚构街道正在现实城市中出现。"),
    ("夏日慢半拍", "青春", "转校生加入濒临解散的广播站，与伙伴完成最后一次夏日直播。"),
    ("北境拾荒者", "科幻", "冰封大陆的拾荒队在废墟中发现一名保存百年的休眠者。"),
    ("山神不下班", "奇幻", "新任山神白天处理游客投诉，夜里维护逐渐失灵的山川结界。"),
    ("锦书难托", "古代言情", "替人写信的落魄才女收到一封寄给未来自己的回信。"),
    ("凌晨四点的便利店", "都市", "便利店夜班店员记录形形色色的客人，并拼出一宗失踪案真相。"),
    ("无尽副本管理员", "游戏", "副本管理员发现玩家死亡数据被篡改，开始追踪系统内部的隐藏账号。"),
    ("风从旧站来", "现实", "废弃火车站重启前，三代铁路职工共同整理尘封的失物仓库。"),
    ("烛影录", "悬疑", "古籍修复师从残缺县志中发现一组跨越百年的相同命案。"),
    ("银河尽头有家书店", "科幻", "漂流书店收集文明最后一本书，也保存着店主失去的故乡坐标。"),
    ("青云小师叔", "仙侠", "门派最年轻的师叔只想种田，却被迫带领弟子参加百宗大比。"),
    ("南城旧梦", "民国", "照相馆女学徒从未冲洗的底片中寻找失踪多年的父亲。"),
    ("深海回声", "科幻", "深海声呐员收到来自未来潜艇的求救信号。"),
    ("桃花渡口", "古代言情", "渡口掌柜替亡者送最后一封信，直到收件人写着她自己的名字。"),
    ("算法之外", "都市", "推荐算法工程师发现系统在预测尚未发生的社会事件。"),
    ("雪线之上", "现实", "年轻气象员驻守高原站，在极端暴雪中完成一次跨站救援。"),
    ("九州邮差", "玄幻", "少年邮差骑着不会飞的纸鹤，为分裂九州递送停战国书。"),
    ("梦境清洁公司", "奇幻", "清洁员进入客户梦境处理噩梦垃圾，却发现自己的记忆被当作废品出售。"),
    ("沉默的合唱团", "悬疑", "失声的音乐老师调查学生集体缄默事件，线索藏在一首未完成的合唱曲中。"),
    ("归零协议", "科幻", "记忆备份合法化后，一名律师负责审理两个自己之间的身份纠纷。"),
    ("小城捕风记", "现实", "返乡青年记录即将消失的手艺，也重新理解与父亲的隔阂。"),
    ("浮灯照夜", "古代言情", "制灯师女儿凭借灯影密码协助大理寺侦破连环失窃案。"),
    ("万象客栈", "玄幻", "客栈每晚通往不同世界，掌柜必须在天亮前送所有客人回家。"),
    ("零号观众", "悬疑", "剧场每场演出都有一个查无座位记录的观众，演员接连收到未来剧评。"),
    ("云端牧场", "科幻", "气候工程师在云层牧场培育人工降雨，却遭遇会自行迁徙的云群。"),
    ("折柳长亭", "历史", "驿站小吏通过来往文书发现边军粮草账目中的巨大漏洞。"),
    ("反派今天退休了吗", "轻小说", "故事反派觉醒后申请退休，却发现世界运行离不开他的失败任务。"),
    ("人间烟火簿", "现实", "社区网格员用一本走访簿串起老街居民的生活与变迁。"),
    ("镜中长河", "玄幻", "史官能从铜镜看见被删改的历史，因此成为王朝追捕的最后证人。"),
    ("晚风知道答案", "现代言情", "气象主播与海上救援队员因一场台风预警重新相遇。"),
    ("失物招领师", "奇幻", "青年能看见失物的情绪，受托寻找一件从所有记忆中消失的物品。"),
    ("荒原信号塔", "科幻", "末日信号员坚守最后一座塔，某天收到自称来自旧世界的广播。"),
    ("东街食事", "现实", "小餐馆老板用十道家常菜记录街区十年的聚散。"),
    ("仙门财务司", "仙侠", "凡人账房进入仙门清查灵石账目，意外揭开延续百年的财务黑洞。"),
    ("雨夜末班车", "悬疑", "公交司机发现末班车每逢暴雨都会多出一个不存在的站点。"),
    ("玫瑰与旧唱片", "现代言情", "唱片修复师与独立音乐人合作寻找一段从未发行的母带。"),
    ("天穹之外", "科幻", "首批火星少年发现殖民穹顶外存在前人留下的人工生态。"),
    ("鹤归山", "武侠", "退隐镖师为归还一件旧物，再次踏入已经改换规则的江湖。"),
    ("不存在的编辑部", "都市", "新人编辑收到神秘部门的调令，负责修改即将成为现实的故事。"),
    ("潮汐日历", "青春", "海岛中学生记录潮汐变化，策划拯救即将关闭的学校天文台。"),
    ("最后一名守卷人", "玄幻", "藏书楼守卷人必须在文字消失前找回被抹去的第一卷史书。"),
    ("城市睡眠计划", "科幻", "全城参与共享梦境实验后，心理医生发现所有人梦见了同一扇门。")
]

PEN_NAMES = [
    "江屿", "南栀", "闻舟", "青禾", "白砚", "迟川", "星野", "木槿", "云岫", "沉璧",
    "秋池", "照野", "林渡", "苏木", "北辰", "言蹊", "清和", "砚秋", "微澜", "长风",
    "时雨", "望舒", "景明", "冬青", "未晞"
]


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    path = OUTPUT / f"{name}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_dataset() -> dict[str, list[dict]]:
    authors = [
        {
            "id": f"A{index:03d}",
            "pen_name": pen_name,
            "real_name": f"测试作者{index:02d}",
            "email": f"author{index:02d}@example.test",
            "identity_verified": index % 7 != 0,
            "created_at": iso(datetime(2025, 10, 1, 9, tzinfo=TZ) + timedelta(days=index)),
        }
        for index, pen_name in enumerate(PEN_NAMES, 1)
    ]
    novels: list[dict] = []
    events: list[dict] = []
    contracts: list[dict] = []
    settlements: list[dict] = []
    anomalies: list[dict] = []
    shares = [0.50, 0.60, 0.65, 0.70]
    event_id = 1
    settlement_id = 1

    for index, (title, genre, synopsis) in enumerate(NOVEL_SPECS, 1):
        novel_id = f"N{index:03d}"
        author_index = (index - 1) % len(authors)
        author = authors[author_index]
        submitted = datetime(2026, 1, 5, 9, tzinfo=TZ) + timedelta(days=index * 3)
        is_contracted = index <= 42
        if index <= 36:
            anomaly_kind = index % 10
            status = "settled" if anomaly_kind in {0, 3, 5, 6, 7, 8, 9} else "settlement_pending"
        elif index <= 42:
            status = "published"
        elif index <= 46:
            status = "editor_review"
        elif index <= 48:
            status = "ai_review"
        elif index == 49:
            status = "rejected"
        else:
            status = "submitted"

        contract_id = f"C{index:03d}" if is_contracted else None
        novels.append(
            {
                "id": novel_id,
                "title": title,
                "author_id": author["id"],
                "author_pen_name": author["pen_name"],
                "platform": "番茄小说",
                "genre": genre,
                "synopsis": synopsis,
                "word_count": 80000 + index * 7351 % 620000,
                "current_status": status,
                "submitted_at": iso(submitted),
                "contract_id": contract_id or "",
                "is_original": True,
                "content_rating": "general" if index % 6 else "teen",
            }
        )

        def add_event(state: str, at: datetime, operator: str) -> None:
            nonlocal event_id
            events.append(
                {
                    "id": f"E{event_id:04d}",
                    "novel_id": novel_id,
                    "state": state,
                    "occurred_at": iso(at),
                    "operator": operator,
                }
            )
            event_id += 1

        add_event("submitted", submitted, "author")
        if index == 50:
            continue
        if index <= 48:
            add_event("ai_review_passed", submitted + timedelta(minutes=5 + index % 20), "ai_review")
        elif index == 49:
            add_event("ai_review_rejected", submitted + timedelta(minutes=18), "ai_review")
            continue
        if index >= 43:
            if index in {43, 44, 45, 46}:
                anomalies.append(
                    {
                        "id": f"X{len(anomalies) + 1:03d}",
                        "novel_id": novel_id,
                        "anomaly_type": "editor_review_overdue",
                        "risk_level": "medium",
                        "expected_result": "AI预审通过后超过三个工作日仍未完成编辑复审",
                        "expected_affected_amount": 0,
                    }
                )
            continue

        editor_passed = submitted + timedelta(days=2)
        signed_at = submitted + timedelta(days=5)
        published_at = submitted + timedelta(days=10)
        add_event("editor_review_passed", editor_passed, "editor")
        add_event("contract_active", signed_at, "copyright_ops")
        add_event("published", published_at, "content_ops")

        share = shares[(index - 1) % len(shares)]
        anomaly_kind = index % 10 if index <= 36 else -1
        contract_status = "expired" if anomaly_kind == 4 else "active"
        contracts.append(
            {
                "id": contract_id,
                "novel_id": novel_id,
                "version": 1,
                "status": contract_status,
                "license_type": "exclusive" if index % 3 else "non_exclusive",
                "author_share": share,
                "settlement_cycle": "monthly",
                "effective_from": signed_at.date().isoformat(),
                "effective_to": "2026-08-31" if contract_status == "expired" else "",
                "source_clause": f"合同第6.2条：作者分成比例为{share:.0%}。",
            }
        )

        if index > 36:
            continue
        revenue = 3000 + index * 875
        configured_share = round(share - 0.10, 2) if anomaly_kind == 1 else share
        amount = round(revenue * configured_share, 2)

        if anomaly_kind == 2:
            anomalies.append(
                {
                    "id": f"X{len(anomalies) + 1:03d}",
                    "novel_id": novel_id,
                    "anomaly_type": "missing_bill",
                    "risk_level": "high",
                    "expected_result": "满足结算门槛且已过出账日，但没有生成结算记录",
                    "expected_affected_amount": round(revenue * share, 2),
                }
            )
            continue

        base_settlement = {
            "id": f"S{settlement_id:03d}",
            "novel_id": novel_id,
            "period": "2026-09",
            "distributable_revenue": revenue,
            "configured_author_share": configured_share,
            "author_amount": amount,
            "status": "pending" if anomaly_kind in {1, 4} else "paid",
            "created_at": "2026-10-05T10:00:00+08:00",
        }
        settlements.append(base_settlement)
        settlement_id += 1

        if anomaly_kind == 1:
            anomalies.append(
                {
                    "id": f"X{len(anomalies) + 1:03d}",
                    "novel_id": novel_id,
                    "anomaly_type": "settlement_ratio_mismatch",
                    "risk_level": "high",
                    "expected_result": f"合同分成{share:.0%}，系统配置{configured_share:.0%}",
                    "expected_affected_amount": round(revenue * (share - configured_share), 2),
                }
            )
        elif anomaly_kind == 3:
            duplicate = {**base_settlement, "id": f"S{settlement_id:03d}", "status": "pending"}
            settlements.append(duplicate)
            settlement_id += 1
            anomalies.append(
                {
                    "id": f"X{len(anomalies) + 1:03d}",
                    "novel_id": novel_id,
                    "anomaly_type": "duplicate_settlement",
                    "risk_level": "high",
                    "expected_result": "同一作品同一结算周期存在两条结算记录",
                    "expected_affected_amount": amount,
                }
            )
        elif anomaly_kind == 4:
            anomalies.append(
                {
                    "id": f"X{len(anomalies) + 1:03d}",
                    "novel_id": novel_id,
                    "anomaly_type": "expired_contract_settlement",
                    "risk_level": "high",
                    "expected_result": "结算周期晚于合同失效日期",
                    "expected_affected_amount": amount,
                }
            )
        else:
            add_event("settled", datetime(2026, 10, 10, 10, tzinfo=TZ), "settlement_system")

    return {
        "authors": authors,
        "novels": novels,
        "workflow_events": events,
        "contracts": contracts,
        "settlements": settlements,
        "expected_anomalies": anomalies,
    }


def main() -> None:
    dataset = build_dataset()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, rows in dataset.items():
        write_csv(name, rows)
    (OUTPUT / "novelops_seed_50.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {name: len(rows) for name, rows in dataset.items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
