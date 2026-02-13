import { createApp } from 'vue';
import App from "./App.vue";
import store from "./store";
import UIkit from "uikit";

import VueObserveVisibility from "vue-observe-visibility";

// Import MD icons
import "material-symbols/outlined.css";

import queryMixin from "@/mixins/labThingsMixins.js";
import modalMixin from "@/mixins/modalMixins.js";

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

// Use visibility observer
app.use(VueObserveVisibility);

// Use global mixins
app.mixin(queryMixin);
app.mixin(modalMixin);

// Use Vuex store
app.use(store);
app.mount("#app");
