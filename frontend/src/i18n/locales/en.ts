export type TranslationSchema = {
  langName: string
  langToggle: string
  langToggleTitle: string

  brand: string
  engineTag: string

  nav: {
    chat: string
    watch: string
    drive: string
    agents: string
    profile: string
    settings: string
  }

  header: {
    selfDriveTitle: string
    selfDriveOn: string
    selfDriveOff: string
    indexSp: string
    indexData: string
    indexLive: string
    indexQuotes: string
  }

  status: {
    connected: string
    connecting: string
    disconnected: string
  }

  chat: {
    selfDrive: string
    on: string
    off: string
    tracking: string
    flipOn: string
    settings: string
    last: string
    verified: string
    placeholderOnline: string
    placeholderOffline: string
    analyze: string
    track: string
    trackingList: string
    add: string
    ticker: string
    removeWatchlist: string
    loading: string
    welcome: string
    analyzing: string
    you: string
    sys: string
    ai: string
  }

  quick: string[]

  queries: {
    analyze: string
    comprehensive: string
  }

  watchlist: {
    title: string
    trackAll: string
    addTicker: string
    add: string
    analyze: string
    remove: string
    hint: string
  }

  selfdrive: {
    title: string
    subtitle: string
    backendOnline: string
    backendOffline: string
    symbols: string
    interval: string
    analyzeOnTick: string
    save: string
    tickNow: string
    status: string
    ticks: string
    lastTick: string
    nextTick: string
    running: string
    enabled: string
    off: string
    lastError: string
    lastPrices: string
  }

  agents: {
    title: string
    subtitle: string
    total: string
    active: string
    errors: string
    engine: string
    tasks: string
    activityLog: string
    names: {
      orchestrator: string
      market_data: string
      fundamentals: string
      technical: string
      sentiment: string
      risk: string
      verifier: string
      self_driving: string
    }
    roles: {
      orchestrator: string
      market_data: string
      fundamentals: string
      technical: string
      sentiment: string
      risk: string
      verifier: string
      self_driving: string
    }
  }

  profile: {
    title: string
    subtitle: string
    displayName: string
    watchlist: string
    strategies: string
    save: string
    chatCount: string
    saved: string
  }

  settings: {
    title: string
    engine: string
    connection: string
    api: string
    websocket: string
    help: string
  }

  footer: {
    online: string
    offline: string
    engine: string
    selfDrive: string
  }
}

export const en: TranslationSchema = {
  langName: 'English',
  langToggle: '中文',
  langToggleTitle: 'Switch to Chinese',

  brand: 'StockAgent',
  engineTag: 'LANGGRAPH',

  nav: {
    chat: 'Chat',
    watch: 'Watch',
    drive: 'Drive',
    agents: 'Agents',
    profile: 'Profile',
    settings: 'Settings',
  },

  header: {
    selfDriveTitle: 'Open Self-Driving controls',
    selfDriveOn: 'SELF-DRIVE · ON · {minutes}m',
    selfDriveOff: 'SELF-DRIVE · OFF',
    indexSp: 'S&P 500',
    indexData: 'DATA',
    indexLive: 'live',
    indexQuotes: 'quotes',
  },

  status: {
    connected: 'CONNECTED',
    connecting: 'CONNECTING',
    disconnected: 'DISCONNECTED',
  },

  chat: {
    selfDrive: 'SELF-DRIVE',
    on: 'ON',
    off: 'OFF',
    tracking: '{symbols} · every {minutes}m',
    flipOn: 'Flip ON to track {ticker}',
    settings: 'SETTINGS →',
    last: 'LAST: {rec}',
    verified: 'VERIFIED',
    placeholderOnline: 'Ask LangGraph to analyze a stock…',
    placeholderOffline: 'Backend offline — check API connection',
    analyze: 'ANALYZE',
    track: 'TRACK',
    trackingList: 'TRACKING',
    add: 'ADD',
    ticker: 'TICKER',
    removeWatchlist: 'Remove from profile watchlist',
    loading: 'loading',
    welcome:
      'Ask for a stock analysis, or enable Self-Driving mode.\n\nStatus/errors appear under **Agents**. Profile stores chat, watchlist, and strategies.',
    analyzing: 'Analyzing',
    you: 'YOU',
    sys: 'SYS',
    ai: 'AI',
  },

  quick: [
    'Analyze NVDA',
    'Should I buy AAPL?',
    'Technical analysis for TSLA',
    'Compare MSFT vs GOOGL',
  ],

  queries: {
    analyze: 'Analyze {ticker}',
    comprehensive: 'Give me a comprehensive analysis of {ticker}',
  },

  watchlist: {
    title: 'WATCHLIST',
    trackAll: 'TRACK ALL',
    addTicker: '+ ADD TICKER',
    add: 'ADD',
    analyze: 'ANALYZE',
    remove: 'REMOVE',
    hint: 'Add/remove updates your profile watchlist automatically.',
  },

  selfdrive: {
    title: 'SELF-DRIVING LOOP',
    subtitle: 'Event-driven price tracking via LangGraph backend',
    backendOnline: 'BACKEND ONLINE',
    backendOffline: 'BACKEND OFFLINE',
    symbols: 'SYMBOLS',
    interval: 'INTERVAL (MINUTES)',
    analyzeOnTick: 'Run LangGraph analysis on each tick',
    save: 'SAVE SETTINGS',
    tickNow: 'TICK NOW',
    status: 'STATUS',
    ticks: 'TICKS',
    lastTick: 'LAST TICK',
    nextTick: 'NEXT TICK',
    running: 'RUNNING',
    enabled: 'ENABLED',
    off: 'OFF',
    lastError: 'Last error: {error}',
    lastPrices: 'LAST PRICES',
  },

  agents: {
    title: 'AGENT FLEET',
    subtitle: 'Specialist boxes · click a card for activity log',
    total: 'TOTAL',
    active: 'ACTIVE',
    errors: 'ERRORS',
    engine: 'ENGINE',
    tasks: 'Tasks',
    activityLog: 'ACTIVITY LOG',
    names: {
      orchestrator: 'Orchestrator',
      market_data: 'Market Data',
      fundamentals: 'Fundamentals',
      technical: 'Technical',
      sentiment: 'Sentiment',
      risk: 'Risk',
      verifier: 'Verifier',
      self_driving: 'Self-Driving',
    },
    roles: {
      orchestrator: 'Routes work and synthesizes the final call',
      market_data: 'Live quotes, volume, and price history',
      fundamentals: 'Valuation, margins, and financial health',
      technical: 'SMA/EMA/RSI and trend structure',
      sentiment: 'News tone and catalyst awareness',
      risk: 'Drawdown, sizing, and downside checks',
      verifier: 'Rubric check before finalizing',
      self_driving: 'Interval price tracking loop',
    },
  },

  profile: {
    title: 'USER PROFILE',
    subtitle: 'Chat history, watchlist, and per-agent strategies',
    displayName: 'DISPLAY NAME',
    watchlist: 'WATCHLIST',
    strategies: 'AGENT STRATEGIES',
    save: 'SAVE PROFILE',
    chatCount: 'Chat messages: {count}',
    saved: 'Profile saved',
  },

  settings: {
    title: 'BACKEND SETTINGS',
    engine: 'Engine',
    connection: 'Connection',
    api: 'API',
    websocket: 'WebSocket',
    help: 'Set VITE_API_URL and VITE_WS_URL in Vercel Environments, then redeploy. On Render, set CORS_ORIGINS to this site URL.',
  },

  footer: {
    online: 'Backend online',
    offline: 'Backend offline',
    engine: 'Engine: {engine}',
    selfDrive: 'Self-drive: {state}',
  },
}
