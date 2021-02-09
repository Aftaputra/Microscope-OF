<template>
  <!-- Grid managing tab content -->
  <div class="uk-height-1-1 view-component">
    <button class="uk-button uk-button-default" type="button">Plugins</button>
    <div uk-dropdown>
      <ul class="uk-nav uk-dropdown-nav">
          <li><a href="#" @click="loadPluginDialog()">Load Plugin</a></li>
          <li class="uk-nav-divider"></li>
          <li><a href="#" @click="runPlugin(p)" v-for="(p, name) in loadedPlugins" :key="p.id"><i class="material-icons">extension</i>{{name}}</a></li>
          <li class="uk-nav-divider"></li>
          <li><a href="#" @click="activeWindow=w" v-for="w in windows" :key="w.id"><i class="material-icons">launch</i>{{w.name}}</a></li>
      </ul>
    </div>

    <div v-show="w===activeWindow" v-for="w in windows" class="uk-card uk-card-body imjoy-container-card" :key="w.id">
        <h3 class="uk-card-title">{{w.name}}</h3>
        <div class="window-container" :id="w.window_id">
          
        </div>
    </div>

    <div class="progress uk-margin-small" v-show="loading">
      <div class="indeterminate"></div>
    </div>
  </div>
</template>



<script>

import * as imjoyCore from 'imjoy-core';

export default {
  name: "ImJoyContent",

  components: {
  },
  data(){
    return {
      windows: {},
      loading: false,
      loadedPlugins: {},
      activeWindow: null
    }
  },
  mounted(){
    const imjoy = new imjoyCore.ImJoy({
        imjoy_api: {},
        //imjoy config
    });
    
    imjoy.start({workspace: 'default'}).then(async ()=>{
        console.log('ImJoy started');
        imjoy.event_bus.on("add_window", async (w) => {
          this.addWindow(w);
        })
        await this.loadPlugin("https://kaibu.org/#/app");
    })
    this.imjoy = imjoy;
  },
  methods:{
    addWindow(w) {
      this.windows = this.windows || {};
      this.windows[w.window_id] = w;
      this.activeWindow = w;
      this.$forceUpdate();
    },
    loadPlugin(uri){
      this.loading = true
      this.imjoy.pm.reloadPluginRecursively({
          uri
      }).then(async (plugin) => {
        this.loadedPlugins[plugin.name] = plugin;
        this.loading = false
      }).catch((e) => {
        console.error(e)
        this.loading = false
        alert(`failed to load the plugin, error: ${e}`)
      })
    },
    async runPlugin(plugin){
      await plugin.api.run()
    },
    loadPluginDialog(){
      const uri = prompt("Paste the ImJoy plugin url here")
      if(uri){
        this.loadPlugin(uri)
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
