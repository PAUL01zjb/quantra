"""行业指标词典（全面版）。

覆盖通用财务 + 银行/证券/保险/地产/消费/医药/科技制造/汽车/能源化工/公用基建等行业，
别名用于抽取归一化（营收 -> 营业收入、净息差 -> 净息差、NBV -> 新业务价值 等）。

说明：规则词典用于确定性抽取与校验；schema-guided LLM 按同一契约抽取时，
规则引擎作为校验归一化通道。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricDef:
    canonical: str
    aliases: list[str]
    unit: str = ""
    kind: str = "amount"  # ratio / amount / per_share / growth / valuation / count
    industries: list[str] = field(default_factory=list)


METRIC_DICTIONARY: list[MetricDef] = [
    # ---------- 通用财务 ----------
    MetricDef("毛利率", ["毛利率", "gross margin", "gross_margin"], "%", "ratio", ["通用"]),
    MetricDef("净利率", ["净利率", "net margin", "net_margin"], "%", "ratio", ["通用"]),
    MetricDef("营业收入", ["营业收入", "营业总收入", "营收", "revenue"], "亿元", "amount", ["通用"]),
    MetricDef("营收增速", ["营收增速", "收入增速", "营业收入同比增长", "营业总收入同比增长", "收入同比增速"], "%", "growth", ["通用"]),
    MetricDef("营业利润", ["营业利润", "经营利润"], "亿元", "amount", ["通用"]),
    MetricDef("净利润", ["净利润", "net profit", "net_profit"], "亿元", "amount", ["通用"]),
    MetricDef("净利润增速", ["净利润增速", "净利润同比增长", "净利润同比增速"], "%", "growth", ["通用"]),
    MetricDef("归母净利润", ["归母净利润", "归母净利", "归属母公司净利润", "归母"], "亿元", "amount", ["通用"]),
    MetricDef("归母净利润增速", ["归母净利润增速", "归母净利增速", "归母净利润同比增长", "归母净利同比"], "%", "growth", ["通用"]),
    MetricDef("ROE", ["ROE", "净资产收益率", "加权平均净资产收益率", "roe"], "%", "ratio", ["通用"]),
    MetricDef("ROA", ["ROA", "总资产收益率", "资产回报率"], "%", "ratio", ["通用"]),
    MetricDef("EPS", ["EPS", "每股收益", "eps"], "元", "per_share", ["通用"]),
    MetricDef("BVPS", ["BVPS", "每股净资产", "每股账面价值"], "元", "per_share", ["通用"]),
    MetricDef("PE", ["PE", "市盈率", "动态市盈率", "pe"], "倍", "valuation", ["通用"]),
    MetricDef("PB", ["PB", "市净率", "pb"], "倍", "valuation", ["通用"]),
    MetricDef("股息率", ["股息率", "分红收益率", "股息收益率"], "%", "ratio", ["通用"]),
    MetricDef("分红率", ["分红率", "股利支付率", "现金分红比例"], "%", "ratio", ["通用"]),
    MetricDef("资产负债率", ["资产负债率"], "%", "ratio", ["通用"]),
    MetricDef("经营现金流", ["经营现金流", "经营性现金流", "经营活动现金流净额", "OCF"], "亿元", "amount", ["通用"]),
    MetricDef("自由现金流", ["自由现金流", "FCF"], "亿元", "amount", ["通用"]),
    MetricDef("总资产", ["总资产", "资产总额"], "亿元", "amount", ["通用"]),
    MetricDef("净资产", ["净资产", "归母净资产", "股东权益"], "亿元", "amount", ["通用"]),
    MetricDef("总市值", ["总市值", "市值"], "亿元", "amount", ["通用"]),
    MetricDef("研发费用率", ["研发费用率", "研发投入占比", "研发强度"], "%", "ratio", ["通用"]),
    MetricDef("销售费用率", ["销售费用率"], "%", "ratio", ["通用"]),
    MetricDef("管理费用率", ["管理费用率"], "%", "ratio", ["通用"]),

    # ---------- 银行业 ----------
    MetricDef("净息差", ["净息差", "NIM", "净利息收益率"], "%", "ratio", ["银行"]),
    MetricDef("净利差", ["净利差"], "%", "ratio", ["银行"]),
    MetricDef("不良贷款率", ["不良贷款率", "不良率"], "%", "ratio", ["银行"]),
    MetricDef("拨备覆盖率", ["拨备覆盖率"], "%", "ratio", ["银行"]),
    MetricDef("拨贷比", ["拨贷比"], "%", "ratio", ["银行"]),
    MetricDef("核心一级资本充足率", ["核心一级资本充足率", "核心资本充足率"], "%", "ratio", ["银行"]),
    MetricDef("一级资本充足率", ["一级资本充足率"], "%", "ratio", ["银行"]),
    MetricDef("资本充足率", ["资本充足率"], "%", "ratio", ["银行"]),
    MetricDef("成本收入比", ["成本收入比"], "%", "ratio", ["银行"]),
    MetricDef("手续费及佣金净收入", ["手续费及佣金净收入", "中间业务收入", "中收"], "亿元", "amount", ["银行"]),
    MetricDef("非息收入", ["非息收入", "非利息收入"], "亿元", "amount", ["银行"]),
    MetricDef("贷款总额", ["贷款总额", "发放贷款及垫款", "贷款余额"], "亿元", "amount", ["银行"]),
    MetricDef("存款总额", ["存款总额", "存款余额", "吸收存款"], "亿元", "amount", ["银行"]),
    MetricDef("生息资产", ["生息资产"], "亿元", "amount", ["银行"]),
    MetricDef("计息负债", ["计息负债"], "亿元", "amount", ["银行"]),

    # ---------- 证券业 ----------
    MetricDef("经纪业务收入", ["经纪业务收入", "代理买卖证券业务净收入", "经纪收入"], "亿元", "amount", ["证券"]),
    MetricDef("投行业务收入", ["投行业务收入", "投资银行业务收入", "投行收入"], "亿元", "amount", ["证券"]),
    MetricDef("资管业务收入", ["资管业务收入", "资产管理业务收入", "资管收入"], "亿元", "amount", ["证券"]),
    MetricDef("自营业务收入", ["自营业务收入", "证券投资业务收入", "自营收入"], "亿元", "amount", ["证券"]),
    MetricDef("利息净收入", ["利息净收入", "利息收入净额"], "亿元", "amount", ["证券"]),
    MetricDef("其他业务收入", ["其他业务收入"], "亿元", "amount", ["证券"]),
    MetricDef("两融余额", ["两融余额", "融资融券余额"], "亿元", "amount", ["证券"]),
    MetricDef("市占率", ["市占率", "市场份额", "经纪业务市占率"], "%", "ratio", ["证券"]),

    # ---------- 保险业 ----------
    MetricDef("新业务价值", ["新业务价值", "NBV"], "亿元", "amount", ["保险"]),
    MetricDef("内含价值", ["内含价值", "EV"], "亿元", "amount", ["保险"]),
    MetricDef("保费收入", ["保费收入", "原保费收入", "总保费"], "亿元", "amount", ["保险"]),
    MetricDef("新业务价值率", ["新业务价值率", "NBV margin", "NBV Margin"], "%", "ratio", ["保险"]),
    MetricDef("综合偿付能力充足率", ["综合偿付能力充足率"], "%", "ratio", ["保险"]),
    MetricDef("核心偿付能力充足率", ["核心偿付能力充足率"], "%", "ratio", ["保险"]),
    MetricDef("总投资收益率", ["总投资收益率", "综合投资收益率"], "%", "ratio", ["保险"]),
    MetricDef("净投资收益率", ["净投资收益率"], "%", "ratio", ["保险"]),
    MetricDef("综合成本率", ["综合成本率"], "%", "ratio", ["保险"]),
    MetricDef("赔付率", ["赔付率", "综合赔付率"], "%", "ratio", ["保险"]),

    # ---------- 房地产 ----------
    MetricDef("销售金额", ["销售金额", "合约销售额", "合同销售金额", "全口径销售金额"], "亿元", "amount", ["地产"]),
    MetricDef("销售面积", ["销售面积", "合约销售面积"], "万平方米", "amount", ["地产"]),
    MetricDef("拿地金额", ["拿地金额", "权益拿地金额"], "亿元", "amount", ["地产"]),
    MetricDef("合同负债", ["合同负债", "预收账款"], "亿元", "amount", ["地产"]),
    MetricDef("净负债率", ["净负债率"], "%", "ratio", ["地产"]),
    MetricDef("土地储备", ["土地储备", "土储", "储备面积"], "万平方米", "amount", ["地产"]),
    MetricDef("结算收入", ["结算收入", "地产结算收入"], "亿元", "amount", ["地产"]),
    MetricDef("竣工面积", ["竣工面积"], "万平方米", "amount", ["地产"]),
    MetricDef("新开工面积", ["新开工面积"], "万平方米", "amount", ["地产"]),

    # ---------- 消费/零售 ----------
    MetricDef("门店数", ["门店数", "门店数量", "店铺数"], "家", "count", ["消费"]),
    MetricDef("单店收入", ["单店收入"], "万元", "amount", ["消费"]),
    MetricDef("同店增速", ["同店增速", "同店增长", "可比店增速", "可比同店增速"], "%", "growth", ["消费"]),
    MetricDef("线上收入占比", ["线上收入占比", "电商收入占比"], "%", "ratio", ["消费"]),
    MetricDef("客单价", ["客单价"], "元", "amount", ["消费"]),

    # ---------- 医药 ----------
    MetricDef("研发投入", ["研发投入", "研发费用"], "亿元", "amount", ["医药"]),
    MetricDef("在研管线", ["在研管线", "管线数量", "临床管线"], "个", "count", ["医药"]),
    MetricDef("创新药收入", ["创新药收入", "创新药销售"], "亿元", "amount", ["医药"]),
    MetricDef("授权首付款", ["授权首付款", "License-out 首付款", "首付款"], "亿美元", "amount", ["医药"]),

    # ---------- 科技/制造 ----------
    MetricDef("存货周转天数", ["存货周转天数"], "天", "amount", ["科技制造"]),
    MetricDef("应收账款周转天数", ["应收账款周转天数"], "天", "amount", ["科技制造"]),
    MetricDef("产能利用率", ["产能利用率", "稼动率"], "%", "ratio", ["科技制造"]),
    MetricDef("在手订单", ["在手订单", "订单金额"], "亿元", "amount", ["科技制造"]),
    MetricDef("新签订单", ["新签订单", "新增订单"], "亿元", "amount", ["科技制造"]),

    # ---------- 汽车 ----------
    MetricDef("销量", ["销量", "整车销量"], "万辆", "amount", ["汽车"]),
    MetricDef("产量", ["产量", "整车产量"], "万辆", "amount", ["汽车"]),
    MetricDef("单车均价", ["单车均价", "ASP"], "万元", "amount", ["汽车"]),
    MetricDef("新能源销量占比", ["新能源销量占比", "新能源车销量占比", "新能源渗透率"], "%", "ratio", ["汽车"]),

    # ---------- 能源/化工 ----------
    MetricDef("产量", ["产量"], "万吨", "amount", ["能源化工"]),
    MetricDef("销量", ["销量", "销售量"], "万吨", "amount", ["能源化工"]),
    MetricDef("吨毛利", ["吨毛利"], "元/吨", "amount", ["能源化工"]),
    MetricDef("开工率", ["开工率", "装置开工率"], "%", "ratio", ["能源化工"]),
    MetricDef("库存", ["库存", "库存量"], "万吨", "amount", ["能源化工"]),

    # ---------- 公用/基建 ----------
    MetricDef("新签合同额", ["新签合同额", "新签订单额"], "亿元", "amount", ["公用基建"]),
    MetricDef("发电量", ["发电量"], "亿千瓦时", "amount", ["公用基建"]),
    MetricDef("售电量", ["售电量"], "亿千瓦时", "amount", ["公用基建"]),
    MetricDef("上网电量", ["上网电量"], "亿千瓦时", "amount", ["公用基建"]),
    MetricDef("装机容量", ["装机容量"], "万千瓦", "amount", ["公用基建"]),
]

INDUSTRIES: list[str] = sorted({ind for m in METRIC_DICTIONARY for ind in m.industries})


def metric_def(name: str) -> MetricDef | None:
    lowered = name.lower()
    for definition in METRIC_DICTIONARY:
        if name == definition.canonical or lowered in [a.lower() for a in definition.aliases]:
            return definition
    return None


def normalize_metric_name(name: str) -> str | None:
    definition = metric_def(name)
    return definition.canonical if definition else None
