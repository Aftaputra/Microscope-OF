<template>
  <!-- Grid managing tab content -->
  <div class="uk-height-1-1 view-component">
    <progress
      ref="imjoyProgressbar"
      style="height: 4px; margin-bottom:0!important"
      class="uk-progress"
      max="100"
    ></progress>
    <button
      v-if="activeWindow"
      class="uk-button uk-button-default close-button"
      type="button"
      @click="closeActiveWindow()"
    >
      <i class="material-icons">close</i>
    </button>
    <button class="uk-button uk-button-default plugins-button" type="button">
      <img
        style="width:18px;"
        src="https://imjoy.io/static/img/imjoy-icon.svg"
      />&nbsp;Plugins
    </button>
    <div uk-dropdown>
      <ul class="uk-nav uk-dropdown-nav">
        <li>
          <a href="#" @click="loadPluginDialog()">
            <i class="material-icons">add</i>&nbsp; Load Plugin</a
          >
        </li>
        <li
          v-if="Object.keys(loadedPlugins).length > 0"
          class="uk-nav-divider"
        ></li>
        <li>
          <a href="#" @click="startImageJ()"
            ><img
              alt="ImageJ.JS icon"
              style="width:20px;"
              src="https://ij.imjoy.io/assets/icons/chrome/chrome-installprocess-128-128.png"
            />&nbsp;ImageJ.JS</a
          >
        </li>
        <li>
          <a href="#" @click="startKaibu()"
            ><img
              alt="Kaibu icon"
              style="width:20px;"
              src="https://kaibu.org/static/img/kaibu-icon.svg"
            />&nbsp;Kaibu</a
          >
        </li>
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
            ><i class="material-icons">filter_none</i>&nbsp;{{ w.name }}</a
          >
        </li>
      </ul>
    </div>

    <div
      v-for="w in windows"
      v-show="w === activeWindow"
      :key="w.id"
      style="height: 100%;"
    >
      <h4 class="window-title">{{ w.name }}</h4>
      <div :id="w.window_id" class="window-container"></div>
    </div>
    <div
      v-if="!activeWindow || windows.length <= 0"
      class="uk-position-center position-relative text-center"
    >
      <img
        style="width:80px;"
        src="https://imjoy.io/static/img/imjoy-icon.svg"
      />
    </div>

    <div v-show="loading" class="progress uk-margin-small">
      <div class="indeterminate"></div>
    </div>
  </div>
</template>

<script>
import * as imjoyCore from "imjoy-core";
import axios from "axios";
import UIkit from "uikit";

export default {
  name: "ImJoyContent",

  components: {},
  data() {
    return {
      windows: [],
      loading: false,
      loadedPlugins: {},
      activeWindow: null,
      viewers: {}
    };
  },
  computed: {
    captureActionUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/actions/camera/capture`;
    },
    snapshotStreamUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/streams/snapshot`;
    },
    getPositionUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/state/stage/position`;
    },
    moveActionUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/actions/stage/move`;
    }
  },
  mounted() {
    const self = this;
    const imjoy = new imjoyCore.ImJoy({
      imjoy_api: {
        async showDialog(plugin, config, exta_config) {
          return await imjoy.pm.createWindow(plugin, config, exta_config);
        },
        async showSnackbar(plugin, msg, duration) {
          duration = duration || 5;
          UIkit.notification.closeAll();
          UIkit.notification({
            message: msg.slice(0, 100),
            status: "primary",
            pos: "bottom-center",
            timeout: duration * 1000
          });
        },
        async showMessage(plugin, msg) {
          imjoy.imjoy_api.showSnackbar(plugin, msg, 5);
        },
        async showStatus(plugin, status) {
          imjoy.imjoy_api.showSnackbar(plugin, status, 5);
        },
        async showProgress(plugin, p) {
          p = p || 0;
          if (p < 1.0) p = p * 100;
          if (p > 100) p = 100;
          if (p) {
            self.$refs.imjoyProgressbar.style.display = "block";
            self.$refs.imjoyProgressbar.value = parseInt(p);
          } else {
            self.$refs.imjoyProgressbar.style.display = "none";
          }
        }
      }
    });

    imjoy.start({ workspace: "default" }).then(() => {
      console.log("ImJoy started");
      imjoy.event_bus.on("add_window", w => {
        this.addWindow(w);
      });
      this.setupMicroscopeAPI();
      this.setupViewers();
      // load the script editor for openflexure
      this.loadPlugin(
        "https://gist.githubusercontent.com/oeway/7a9dcb49c51b1f99b2c3619f470fe35c/raw/OpenFlexureScriptEditor.imjoy.html"
      );
      this.setupPluginEngine();
    });
    this.imjoy = imjoy;
  },
  methods: {
    setupPluginEngine() {
      // setup a plugin engine for Python plugins
      this.imjoy.pm
        .reloadPluginRecursively({
          uri:
            "https://imjoy-team.github.io/jupyter-engine-manager/Jupyter-Engine-Manager.imjoy.html"
        })
        .then(enginePlugin => {
          // TODO: currently the url query  are not preserved for ImJoy
          const queryString = window.location.search;
          const urlParams = new URLSearchParams(queryString);
          const engine = urlParams.get("engine");
          const spec = urlParams.get("spec");
          if (engine) {
            enginePlugin.api
              .createEngine({
                name: "MyCustomEngine",
                nbUrl: engine,
                url: engine.split("?")[0]
              })
              .then(() => {
                console.log("Jupyter Engine connected!");
              })
              .catch(e => {
                console.error("Failed to connect to Jupyter Engine", e);
              });
          } else {
            enginePlugin.api
              .createEngine({
                name: "MyBinder Engine",
                url: "https://mybinder.org",
                spec: spec || "oeway/imjoy-binder-image/master"
              })
              .then(() => {
                console.log("Binder Engine connected!");
              })
              .catch(e => {
                console.error("Failed to connect to MyBinder Engine", e);
              });
          }
        });
    },
    setupMicroscopeAPI() {
      // Here we register a set of API for controlling the microscope as an service
      // For interoperatability, it might be good to reuse a subset of the function names defined in MicroManager
      // See here: https://valelab4.ucsf.edu/~MM/doc/MMCore/html/class_c_m_m_core.html
      const snapshotUri = this.snapshotStreamUri;
      const captureActionUri = this.captureActionUri;
      const getPositionUri = this.getPositionUri;
      const moveActionUri = this.moveActionUri;
      const modalError = this.modalError;
      async function pollUntilComplete(response) {
        // Poll an action until its status is completed
        // TODO: raise an error if it fails or is cancelled
        // For ease, this accepts and returns a response object from
        // axios.get
        // FIXME: this could be an infinite loop if the task is cancelled/errored
        let r = response;
        while (r.data.status == "active") {
          await new Promise(resolve => setTimeout(resolve, 100));
          r = await axios.get(r.data.href);
        }
        return r;
      }
      const service = {
        type: "_microscope-control",
        name: "OpenFlexure",
        lastSnapResponse: null,
        snapPreviewImage() {
          // The "proper" capture method is more involved - this one pulls a frame out of the preview stream
          return axios
            .get(snapshotUri)
            .then(response => {
              return response.data;
            })
            .catch(modalError);
        },
        snapImage() {
          // Do capture
          return axios.post(captureActionUri, {}).then(response => {
            service.lastSnapResponse = response;
            // TODO: send the events to flash the stream and update captures
            // Flash the stream (capture animation)
            //this.$root.$emit("globalFlashStream");
            // Update the global capture list
            //this.$root.$emit("globalUpdateCaptures");
          });
          //.catch(modalError);
        },
        async getImage() {
          // FIXME: handle nicely getImage() being called before snapImage()
          // Wait until the capture has completed and we can retrieve it
          service.lastSnapResponse = await pollUntilComplete(
            service.lastSnapResponse
          );
          let capture = service.lastSnapResponse.data.output;
          // TODO: check links.download.href exists and is JPEG
          let jpeg = await axios
            .get(capture.links.download.href, {
              responseType: "arraybuffer",
              headers: {
                "Content-Type": "image/jpeg"
              }
            })
            .then(r => r.data);
          console.log(
            "Downloaded ",
            jpeg.byteLength,
            " bytes of JPEG image data"
          );
          return jpeg; //TODO: what is the expected output format???
        },
        setPosition(z) {
          // The C api suggests this defaults to just Z, and can accept a "label" to
          // select the stage.
          return service.setXYZPosition({
            "z": z,
            "absolute": true,
          });
        },
        async getPosition() {
          const pos = await service.getXYZPosition();
          return pos.z;
        },
        async setXYPosition(x, y) {
          return service.setXYZPosition({
            "x": x,
            "y": y,
            "absolute": true,
          });
        },
        async getXYPosition() {
          const pos = await service.getXYZPosition();
          return [pos.x, pos.y];
        },
        async getXYZPosition() {
          return axios
            .get(getPositionUri)
            .then(r => r.data)
        },
        async setXYZPosition(payload) {
          return axios
            .post(moveActionUri, payload)
            .then(pollUntilComplete)
        }
      };
      this.imjoy.pm.registerService({ name: "openflexure" }, service);
    },
    closeActiveWindow() {
      if (this.activeWindow) {
        this.activeWindow.api.close();
        const index = this.windows.indexOf(this.activeWindow);
        if (index > -1) {
          this.windows.splice(index, 1);
        }
        if (this.windows.length > 0) {
          this.activeWindow = this.windows[this.windows.length - 1];
        } else {
          this.activeWindow = null;
        }
      }
    },
    selectWindow(name) {
      for (let w of this.windows) {
        if (w.name === name) {
          this.activeWindow = w;
          break;
        }
      }
    },
    async startKaibu() {
      this.viewers.kaibu = await this.imjoy.pm.createWindow(null, {
        name: "Kaibu",
        src: "https://kaibu.org/#/app"
      });
      this.viewers.kaibu.on("close", () => {
        delete this.viewers.kaibu;
      });
      this.viewers.kaibu.set_mode("full");
      this.selectWindow("Kaibu");
    },
    async startImageJ() {
      this.viewers.imagej = await this.imjoy.pm.createWindow(null, {
        name: "ImageJ.JS",
        src: "https://ij.imjoy.io"
      });
      this.viewers.imagej.on("close", () => {
        delete this.viewers.imagej;
      });
      // load the ITK/VTK viewer for imagej.js
      this.loadPlugin(
        "https://gist.githubusercontent.com/oeway/e5c980fbf6582f25fde795262a7e33ec/raw/itk-vtk-viewer-imagej.imjoy.html"
      );
      this.selectWindow("ImageJ.JS");
    },
    async setupViewers() {
      this.loading = true;
      // TODO: improve this using the ImJoy `api.getServices`
      // See here: https://imjoy.io/docs/#/api?id=apigetservices
      // The idea is that plugins can register custom services via `api.registerService`
      // For example, we can have a image visualization service
      // Then other plugins can use `api.getServices` to get a list of services
      // And this can be used for render our "Open In ImJoy" menu
      try {
        const self = this;

        this.$store.commit("addOpenInImjoyMenuItem", {
          title: "Kaibu",
          async callback(name, imageUrl) {
            self.$root.$emit("globalSwitchTab", "ImJoy");
            if (!self.viewers.kaibu) {
              await self.startKaibu();
            }
            self.selectWindow("Kaibu");
            const viewer = self.viewers.kaibu;
            await viewer.view_image(imageUrl, { type: "2d-image", name });
            await viewer.add_shapes([]);
          }
        });

        this.$store.commit("addOpenInImjoyMenuItem", {
          title: "ImageJ.JS",
          async callback(name, imageUrl) {
            self.$root.$emit("globalSwitchTab", "ImJoy");
            if (!self.viewers.imagej) {
              await self.startImageJ();
            }
            self.selectWindow("ImageJ.JS");
            const viewer = self.viewers.imagej;
            const response = await fetch(imageUrl);
            const buffer = await response.arrayBuffer();
            await viewer.viewImage(buffer, {
              name: name.replace(".jpeg", ".jpg")
            });
          }
        });
      } catch (e) {
        alert(`Failed to setup viewers, error: ${e}`);
      } finally {
        this.loading = false;
      }
    },
    addWindow(w) {
      this.windows = this.windows || [];
      this.windows.push(w);
      this.activeWindow = w;
      this.$forceUpdate();
    },
    loadPlugin(uri) {
      return new Promise((resolve, reject) => {
        this.loading = true;
        this.imjoy.pm
          .reloadPluginRecursively({
            uri
          })
          .then(async plugin => {
            this.loadedPlugins[plugin.name] = plugin;
            this.loading = false;
            resolve(plugin);
          })
          .catch(e => {
            console.error(e);
            this.loading = false;
            reject(e);
            alert(`failed to load the plugin, error: ${e}`);
          });
      });
    },
    async runPlugin(plugin) {
      await plugin.api.run();
    },
    loadPluginDialog() {
      const uri = prompt(
        "Paste the ImJoy plugin url here",
        "imjoy-team/imjoy-plugins:Welcome"
      );
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

.window-title {
  height: 26px;
  text-align: center;
  font-size: 1.2rem;
  background-color: #efefef;
  color: #482727;
  font-weight: 500;
}

.plugins-button {
  position: absolute;
  right: 1px;
  height: 26px;
  line-height: 11px;
}

.close-button {
  position: absolute;
  right: 100px;
  height: 26px;
}
</style>
