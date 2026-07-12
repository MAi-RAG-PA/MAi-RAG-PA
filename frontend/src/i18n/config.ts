import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: { translation: { "app.title": "MAi-RAG Personal Assistant", "chat.placeholder": "Type your message..." } },
  es: { translation: { "app.title": "Asistente Personal MAi-RAG", "chat.placeholder": "Escribe tu mensaje..." } }
};

i18n.use(initReactI18next).init({ resources, lng: 'en', fallbackLng: 'en', interpolation: { escapeValue: false } });
export default i18n;
