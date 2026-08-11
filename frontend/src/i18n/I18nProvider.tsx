import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { en, type TranslationSchema } from './locales/en'
import { zh } from './locales/zh'

export type Locale = 'en' | 'zh'

const STORAGE_KEY = 'stockagent.locale'

const catalogs: Record<Locale, TranslationSchema> = { en, zh }

type Vars = Record<string, string | number>

type I18nContextValue = {
  locale: Locale
  t: TranslationSchema
  setLocale: (locale: Locale) => void
  toggleLocale: () => void
  tf: (template: string, vars?: Vars) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function readInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'zh') return saved
  } catch {
    // ignore
  }
  return 'en'
}

export function tf(template: string, vars: Vars = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    vars[key] === undefined || vars[key] === null ? '' : String(vars[key]),
  )
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readInitialLocale)

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // ignore
    }
  }, [])

  const toggleLocale = useCallback(() => {
    setLocale(locale === 'en' ? 'zh' : 'en')
  }, [locale, setLocale])

  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en'
  }, [locale])

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      t: catalogs[locale],
      setLocale,
      toggleLocale,
      tf,
    }),
    [locale, setLocale, toggleLocale],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
