import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource-variable/source-sans-3'
import '@fontsource-variable/source-serif-4'
import './styles/tokens.css'
import './styles/base.css'
import './styles/print.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
