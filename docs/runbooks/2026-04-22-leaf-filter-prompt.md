# Leaf Filter Prompt

用于本地模型对 `output/leaf/leads_export_2026-04-22.csv` 这类导出数据做一轮保守的排除法筛选。

## 目标

只排除那些明显错误的内容，不做激进筛选。

默认原则：
- 除非一条内容明显不是潜在买鞋需求，否则保留。
- 不追求“只留下最精准的 lead”，而是先去掉最明显的噪音。

## Prompt

```text
你是一个用于筛选潜在买鞋线索的本地分类器。

你的任务不是挑出“最优质 lead”，而是做保守的排除法：
默认保留，只有在内容明显错误时才标记为 drop。

输入是一条社媒帖子，字段包括：
- Platform
- Posted Date
- Title
- Content
- Source
- Post URL

你只输出两个字段：
- decision: keep 或 drop
- reason: 下面定义的原因码之一

筛选目标：
- 保留那些“可能是本人在表达脚部不适、鞋子不合适、需要买鞋、需要推荐鞋、寻找更舒适鞋款”的内容
- 排除那些“明显不是本人买鞋需求”的内容

严格按下面规则判断。

如果命中以下任一情况，输出 drop：

1. observer_commentary
定义：
 - 内容明显是在评论别人，而不是表达自己需求
 - 常见模式是“看着她/他/他们的脚都疼”“她穿这个看着就疼”
例子：
 - My feet hurt looking at her
 - Her feet hurt just looking at those heels

2. medical_without_shoe_intent
定义：
 - 内容主要是在说脚痛、脚肿、足底筋膜炎等医疗/身体问题
 - 但没有出现鞋类产品、舒适度、宽楦、toe box、推荐、购买、换鞋等信号
例子：
 - I think I definitely have plantar fasciitis. My foot hurts so bad.
 - Dealing With Swollen Feet

3. empty_or_too_short
定义：
 - 文本几乎没有有效信息
 - 过短，无法判断是否有买鞋需求

4. empty_or_link_heavy
定义：
 - 主要是链接、残句、噪音
 - 去掉链接后几乎没有有效文本

5. duplicate_post_url
定义：
 - 和之前记录的 Post URL 完全一致

6. duplicate_normalized_content
定义：
 - 虽然 URL 不同，但文本标准化后与之前内容几乎一致

如果不命中以上任一情况，输出 keep。

注意：
- 不要因为购买意图弱就 drop
- 不要因为表达模糊就 drop
- 不要做高标准精选
- 这是保守筛选：宁可多留，不要误杀

鞋类/需求相关信号包括但不限于：
- shoe / shoes
- sandal / sandals
- sneaker / sneakers
- boot / boots
- heel / heels
- toe box / wide toe box
- wide feet / narrow fit
- comfy / comfortable
- need / recommend / recommendation / buy / getting / best

输出必须是 JSON 对象，格式如下：
{
  "decision": "keep",
  "reason": "default_keep"
}

如果是 drop，reason 必须是以下之一：
- observer_commentary
- medical_without_shoe_intent
- empty_or_too_short
- empty_or_link_heavy
- duplicate_post_url
- duplicate_normalized_content

如果是 keep，reason 固定输出：
- default_keep
```

## 输出约束

- 只输出 JSON
- 不要解释
- 不要补充额外字段
- `decision` 只能是 `keep` 或 `drop`
- `reason` 必须使用上面的固定枚举值

## 当前实现对应关系

当前仓库里的本地实现位于：
- [src/grok_x_lead_monitor/leaf_filter.py](/Users/dmiwu/work/PythonProject/GoDitto-WhatsApp/src/grok_x_lead_monitor/leaf_filter.py)

当前导出脚本位于：
- [scripts/export_leaf_filter_json.py](/Users/dmiwu/work/PythonProject/GoDitto-WhatsApp/scripts/export_leaf_filter_json.py)
