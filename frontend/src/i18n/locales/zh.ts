import type { TranslationSchema } from './en'

export const zh: TranslationSchema = {
  langName: '中文',
  langToggle: 'EN',
  langToggleTitle: '切换到英文',

  brand: 'StockAgent',
  engineTag: 'LANGGRAPH',

  nav: {
    chat: '对话',
    watch: '自选',
    drive: '自动驾驶',
    agents: '智能体',
    profile: '个人',
    settings: '设置',
  },

  header: {
    selfDriveTitle: '打开自动驾驶控制',
    selfDriveOn: '自动驾驶 · 开 · {minutes}分钟',
    selfDriveOff: '自动驾驶 · 关',
    indexSp: '标普500',
    indexData: '数据',
    indexLive: '实时',
    indexQuotes: '行情',
  },

  status: {
    connected: '已连接',
    connecting: '连接中',
    disconnected: '已断开',
  },

  chat: {
    selfDrive: '自动驾驶',
    on: '开',
    off: '关',
    tracking: '{symbols} · 每 {minutes} 分钟',
    flipOn: '开启以跟踪 {ticker}',
    settings: '设置 →',
    last: '最新: {rec}',
    verified: '已验证',
    placeholderOnline: '让 LangGraph 分析一只股票…',
    placeholderOffline: '后端离线 — 请检查 API 连接',
    analyze: '分析',
    track: '跟踪',
    trackingList: '跟踪中',
    add: '添加',
    ticker: '代码',
    removeWatchlist: '从自选列表移除',
    loading: '加载中',
    welcome:
      '可直接提问股票分析，或开启自动驾驶模式。\n\n状态与错误显示在 **智能体** 页。个人页保存对话、自选股与策略。',
    analyzing: '分析中',
    you: '你',
    sys: '系统',
    ai: 'AI',
  },

  quick: ['分析 NVDA', '我该买入 AAPL 吗？', 'TSLA 技术分析', '对比 MSFT 与 GOOGL'],

  queries: {
    analyze: '分析 {ticker}',
    comprehensive: '请对 {ticker} 进行全面分析',
  },

  watchlist: {
    title: '自选股',
    trackAll: '全部跟踪',
    addTicker: '+ 添加代码',
    add: '添加',
    analyze: '分析',
    remove: '移除',
    hint: '添加/移除会自动同步到个人自选列表。',
  },

  selfdrive: {
    title: '自动驾驶循环',
    subtitle: '通过 LangGraph 后端进行事件驱动价格跟踪',
    backendOnline: '后端在线',
    backendOffline: '后端离线',
    symbols: '标的代码',
    interval: '间隔（分钟）',
    analyzeOnTick: '每次心跳运行 LangGraph 分析',
    save: '保存设置',
    tickNow: '立即心跳',
    status: '状态',
    ticks: '心跳次数',
    lastTick: '上次心跳',
    nextTick: '下次心跳',
    running: '运行中',
    enabled: '已启用',
    off: '关闭',
    lastError: '最近错误: {error}',
    lastPrices: '最新价格',
  },

  agents: {
    title: '智能体集群',
    subtitle: '专业分工 · 点击卡片查看活动日志',
    total: '总数',
    active: '活跃',
    errors: '错误',
    engine: '引擎',
    tasks: '任务',
    activityLog: '活动日志',
    names: {
      orchestrator: '编排器',
      market_data: '行情数据',
      fundamentals: '基本面',
      technical: '技术面',
      sentiment: '情绪面',
      risk: '风险',
      verifier: '校验器',
      self_driving: '自动驾驶',
    },
    roles: {
      orchestrator: '分配任务并汇总最终结论',
      market_data: '实时报价、成交量与价格历史',
      fundamentals: '估值、利润率与财务健康',
      technical: '均线/RSI 与趋势结构',
      sentiment: '新闻情绪与催化剂感知',
      risk: '回撤、仓位与下行检查',
      verifier: '定稿前的规则校验',
      self_driving: '定时价格跟踪循环',
    },
  },

  profile: {
    title: '用户资料',
    subtitle: '对话历史、自选股与各智能体策略',
    displayName: '显示名称',
    watchlist: '自选股',
    strategies: '智能体策略',
    save: '保存资料',
    chatCount: '对话条数: {count}',
    saved: '资料已保存',
  },

  settings: {
    title: '后端设置',
    engine: '引擎',
    connection: '连接',
    api: 'API',
    websocket: 'WebSocket',
    help: '在 Vercel Environments 中设置 VITE_API_URL 与 VITE_WS_URL 后重新部署。在 Render 上将 CORS_ORIGINS 设为本站地址。',
  },

  footer: {
    online: '后端在线',
    offline: '后端离线',
    engine: '引擎: {engine}',
    selfDrive: '自动驾驶: {state}',
  },
}
