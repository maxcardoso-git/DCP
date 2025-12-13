import en from "./locales/en.json";
import ptBR from "./locales/pt-BR.json";
import es from "./locales/es.json";

const bundles = {
  en,
  "pt-BR": ptBR,
  es,
};

export function getTranslation(lang, key) {
  const table = bundles[lang] || bundles.en;
  return table[key] || key;
}

export const supportedLangs = [
  { code: "en", label: "English" },
  { code: "pt-BR", label: "Português (BR)" },
  { code: "es", label: "Español" },
];
