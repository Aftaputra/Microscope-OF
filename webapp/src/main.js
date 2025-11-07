import Vue from "vue";
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

// Use visibility observer
Vue.use(VueObserveVisibility);

Vue.config.productionTip = false;

Vue.mixin(queryMixin);
Vue.mixin(modalMixin);

new Vue({
  store,
  render: (h) => h(App),
}).$mount("#app");
