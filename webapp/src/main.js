import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import App from "./App.vue";
import store from "./store";
import UIkit from "uikit";

// Import MD icons
import "material-symbols/outlined.css";

import modalMixin from "@/mixins/modalMixins.js";
import labThingsMixins from "./mixins/labThingsMixins";

// UIKit overrides
UIkit.mixin(
  {
    data: {
      animation: false,
    },
  },
  "accordion",
);

// Create Vue app
const app = createApp(App);
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

// Use global mixins
app.mixin(modalMixin);
app.mixin(labThingsMixins);

// Use Vuex store
app.use(pinia);
app.mount("#app");
