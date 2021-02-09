<template>
  <!-- Grid managing tab content -->
  <div class="uk-height-1-1 view-component">
    <button class="uk-button uk-button-default" type="button">Plugins</button>
    <div uk-dropdown>
      <ul class="uk-nav uk-dropdown-nav">
        <li><a href="#" @click="loadPluginDialog()">Load Plugin</a></li>
        <li class="uk-nav-divider"></li>
        <li>
          <a
            v-for="(p, name) in loadedPlugins"
            :key="p.id"
            href="#"
            @click="runPlugin(p)"
            ><i class="material-icons">extension</i>{{ name }}</a
          >
        </li>
        <li class="uk-nav-divider"></li>
        <li>
          <a v-for="w in windows" :key="w.id" href="#" @click="activeWindow = w"
            ><i class="material-icons">launch</i>{{ w.name }}</a
          >
        </li>
      </ul>
    </div>

    <div
      v-for="w in windows"
      v-show="w === activeWindow"
      :key="w.id"
      class="uk-card uk-card-body imjoy-container-card"
    >
      <h3 class="uk-card-title">{{ w.name }}</h3>
      <div :id="w.window_id" class="window-container"></div>
    </div>

    <div v-show="loading" class="progress uk-margin-small">
      <div class="indeterminate"></div>
    </div>
  </div>
</template>

<script>
import * as imjoyCore from "imjoy-core";

export default {
  name: "ImJoyContent",

  components: {},
  data() {
    return {
      windows: {},
      loading: false,
      loadedPlugins: {},
      activeWindow: null
    };
  },
  mounted() {
    const imjoy = new imjoyCore.ImJoy({
      imjoy_api: {}
      //imjoy config
    });

    imjoy.start({ workspace: "default" }).then(async () => {
      console.log("ImJoy started");
      imjoy.event_bus.on("add_window", async w => {
        this.addWindow(w);
      });
      await this.loadPlugin("https://kaibu.org/#/app");
    });
    this.imjoy = imjoy;
  },
  methods: {
    addWindow(w) {
      this.windows = this.windows || {};
      this.windows[w.window_id] = w;
      this.activeWindow = w;
      this.$forceUpdate();
    },
    loadPlugin(uri) {
      this.loading = true;
      this.imjoy.pm
        .reloadPluginRecursively({
          uri
        })
        .then(async plugin => {
          this.loadedPlugins[plugin.name] = plugin;
          this.registerOpenInImJoy(plugin);
          this.loading = false;
        })
        .catch(e => {
          console.error(e);
          this.loading = false;
          alert(`failed to load the plugin, error: ${e}`);
        });
    },
    registerOpenInImJoy(plugin) {
      let item;
      // TODO: improve this using the ImJoy `api.getServices`
      // See here: https://imjoy.io/docs/#/api?id=apigetservices
      // The idea is that plugins can register custom services via `api.registerService`
      // For example, we can have a image visualization service
      // Then other plugins can use `api.getServices` to get a list of services
      // And this can be used for render our "Open In ImJoy" menu
      if (plugin.name === "Kaibu") {
        item = {
          title: "Kaibu",
          async callback(name, imageUrl) {
            const viewer = await plugin.api.run();
            viewer.set_mode('full');
            await viewer.view_image(imageUrl, {type: '2d-image', name});
          }
        };
      } else if (plugin.name === "ImageJ.JS") {
        item = {
          title: "ImageJ.JS",
          async callback(name, imageUrl) { // eslint-disable-line
            alert("not implemented");
          }
        };
      }
      if (item) this.$store.commit("addOpenInImjoyMenuItem", item);
    },
    async runPlugin(plugin) {
      await plugin.api.run();
    },
    loadPluginDialog() {
      const uri = prompt("Paste the ImJoy plugin url here");
      if (uri) {
        this.loadPlugin(uri);
      }
    }
  }
};
</script>
<style scoped>
.window-container {
  width: 100%;
  height: 100%;
}

.imjoy-container-card {
  width: 100%;
  height: 100%;
}
</style>
