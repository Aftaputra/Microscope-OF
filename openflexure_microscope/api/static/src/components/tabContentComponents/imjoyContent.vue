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

// TODO: move this to a module or something...
async function pollAction(response) {
  // Poll an action until its status is completed
  // TODO: raise an error if it fails or is cancelled
  // For ease, this accepts and returns a response object from
  // axios.get
  // FIXME: this could be an infinite loop if the task is cancelled/errored
  let r = response;
  while ((r.data.status == "running") | (r.data.status == "pending")) {
    await new Promise(resolve => setTimeout(resolve, 100));
    r = await axios.get(r.data.href);
  }
  return r;
}

/**
 * Create a new Image element and wait for it to load.
 *
 * This returns a Promise, so you can "await" the image
 * element rather than needing to add a callback.
 */
function loadImageFromUrl(src) {
  // Create an Image, and return it once it has loaded
  // see https://stackoverflow.com/a/66180709
  // no need to declare async, as it returns a Promise
  return new Promise((resolve, reject) => {
    const img = new Image();
    // We must set crossOrigin="anonymous" in order
    // to avoid security errors when we get the pixel
    // data
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

/**
 * Retrieve an image from a URL, and return the RGB data
 * in a format that can be cast to an ndarray
 *
 * This follows a slightly convoluted recipe, where we
 * "draw" the image, and then extract the pixels from the
 * 2D canvas.
 */
async function imageUrlToNdarray(url) {
  // see https://stackoverflow.com/questions/934012/get-image-data-url-in-javascript
  const img = await loadImageFromUrl(url);
  const canvas = document.createElement("canvas");
  canvas.width = img.width;
  canvas.height = img.height;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, img.width, img.height);
  const imageData = ctx.getImageData(0, 0, img.width, img.height);
  const rgbaData = imageData.data; // This gets the RGBA values as an ArrayBuffer
  // convert RGBA to RGB
  const rgbData = new Uint8Array(new ArrayBuffer(img.height * img.width * 3));
  for (let i = 0; i < img.height; i++) {
    for (let j = 0; j < img.width; j++) {
      const pos = i * img.width + j;
      rgbData[pos * 3] = rgbaData[pos * 4];
      rgbData[pos * 3 + 1] = rgbaData[pos * 4 + 1];
      rgbData[pos * 3 + 2] = rgbaData[pos * 4 + 2];
    }
  }
  return {
    _rtype: "ndarray",
    _rdtype: "uint8",
    _rshape: [img.height, img.width, 3],
    _rvalue: rgbData.buffer
  };
}

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
    },
    baseUri: function() {
      return this.$store.getters.baseUri;
    }
  },
  mounted() {
    const self = this;
    const imjoy = new imjoyCore.ImJoy({
      // We will load the ImJoy plugin base frame via http (instead of https)
      // such that imjoy plugins can access insecured urls
      // however, some browser features won't work (e.g. webrtc)
      // unless we explicitly set `base_frame` in the plugin to
      // https://lib.imjoy.io/default_base_frame.html
      default_base_frame: "http://lib.imjoy.io/default_base_frame.html",
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

    imjoy.start({ workspace: "default" }).then(async () => {
      console.log("ImJoy started");
      imjoy.event_bus.on("add_window", w => {
        this.addWindow(w);
      });
      this.setupMicroscopeAPI();
      this.setupViewers();
      // load the script editor for openflexure
      await this.loadPlugin(
        `${window.location.origin}/OpenFlexureScriptEditor.imjoy.html`
      );
      // Load the snap image template
      await this.loadPlugin(
        `${window.location.origin}/OpenFlexureSnapImageTemplate.imjoy.html`
      );
      // Load the snap image template
      await this.loadPlugin(
        `${window.location.origin}/OpenFlexureTestMoveStage.imjoy.html`
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
      const modalError = this.modalError;
      const getPositionAsObject = this.getStagePosition;
      const setPositionAsObject = this.setStagePosition;

      const service = {
        _rintf: true, // this will make sure the function can be called multiple times
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
          service.lastSnapResponse = await pollAction(service.lastSnapResponse);
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
          return setPositionAsObject({
            z: z,
            absolute: true
          });
        },
        async getPosition() {
          const { z } = await getPositionAsObject();
          return z;
        },
        async setXYPosition(x, y) {
          return setPositionAsObject({
            x: x,
            y: y,
            absolute: true
          });
        },
        async getXYPosition() {
          const { x, y } = await getPositionAsObject();
          return [x, y];
        },
        async getXYZPosition() {
          const { x, y, z } = await getPositionAsObject();
          return [x, y, z];
        },
        async setXYZPosition(x, y, z) {
          return setPositionAsObject({
            x: x,
            y: y,
            z: z,
            absolute: true
          });
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
    /**
     * Switch to the ImageJ window, starting it if necessary.
     */
    async openImageJ() {
      this.$root.$emit("globalSwitchTab", "ImJoy");
      if (!this.viewers.imagej) {
        await this.startImageJ();
      }
      this.selectWindow("ImageJ.JS");
      return this.viewers.imagej;
    },
    /**
     * Switch to the Kaibu window, starting it if necessary.
     */
    async openKaibu() {
      this.$root.$emit("globalSwitchTab", "ImJoy");
      if (!this.viewers.kaibu) {
        await this.startKaibu();
      }
      this.selectWindow("Kaibu");
      return this.viewers.kaibu;
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

        /*async function obtainImageJ() {
          self.$root.$emit("globalSwitchTab", "ImJoy");
          if(!self.viewers.imagej) {
            await self.startImageJ();
          }
          self.selectWindow("ImageJ.JS");
          return self.viewers.imagej;
        }*/

        this.$store.commit("addOpenInImjoyMenuItem", {
          title: "Kaibu",
          async callback(name, imageUrl) {
            const viewer = await self.openKaibu();
            await viewer.view_image(imageUrl, { type: "2d-image", name });
            await viewer.add_shapes([]);
          }
        });

        this.$store.commit("addOpenInImjoyMenuItem", {
          title: "ImageJ.JS",
          async callback(name, imageUrl) {
            const viewer = await self.openImageJ();
            const response = await fetch(imageUrl);
            const buffer = await response.arrayBuffer();
            await viewer.viewImage(buffer, {
              name: name.replace(".jpeg", ".jpg")
            });
          }
        });
        this.$store.commit("addOpenInImjoyMenuItem", {
          title: "ImageJ.JS [ndarray]",
          async callback(name, imageUrl) {
            const viewer = await self.openImageJ();
            const ndarray = await imageUrlToNdarray(imageUrl);
            await viewer.viewImage(ndarray, {
              name: name.replace(".jpeg", "")
            });
          }
        });
        this.$store.commit("addOpenScanInImjoyMenuItem", {
          title: "ImageJ.JS",
          async callback(name, allURLs) {
            const viewer = await self.openImageJ();
            // allURLs is a list of URLs for *capture objects*, so
            // first we need to retrieve them, then extract image URLs
            // and finally turn image URLs into "numpy arrays" (RGB data).
            const imagesAsNdarrays = await Promise.all(
              allURLs.map(async url => {
                const r = await axios.get(url);
                return imageUrlToNdarray(r.data.links.download.href);
              })
            );
            // Construct an array to hold all the images, based on the first image
            // TODO: assert that _rdtype is uint8, _rshape is the same, _rtype is ndarray
            const shape = imagesAsNdarrays[0]._rshape;
            const totalSize = imagesAsNdarrays.reduce(
              (total, image) => total + image._rvalue.byteLength,
              0
            );
            const stackData = new Uint8Array(new ArrayBuffer(totalSize));
            const transferredBytes = imagesAsNdarrays.reduce((total, image) => {
              console.log(`inserting image at ${total} bytes`);
              // TODO: is it bad to populate stackData as a "side effect"?
              stackData.set(image._rvalue, total);
              //assert image._rshape == shape;
              return total + image._rvalue.byteLength;
            }, 0);
            const stackNdarray = {
              _rtype: "ndarray",
              _rdtype: "uint8",
              _rshape: [imagesAsNdarrays.length, shape[0], shape[1], shape[2]],
              _rdata: stackData
            };
            console.log(
              `Stack is ${transferredBytes} and will have shape: ${stackNdarray._rshape}`
            );
            await viewer.viewImage(stackNdarray, {
              name: "ScanImages"
            });
          }
        });
        this.$store.commit("addOpenScanInImjoyMenuItem", {
          title: "ImageJ.JS [JPEGs]",
          async callback(name, allURLs) {
            const viewer = await self.openImageJ();
            // allURLs is a list of URLs for *capture objects*, so
            // first we need to retrieve them, then extract image URLs
            // and finally turn image URLs into "numpy arrays" (RGB data).
            await Promise.all(
              allURLs.map(async url => {
                const r = await axios.get(url);
                const ndarray = await imageUrlToNdarray(
                  r.data.links.download.href
                );
                return viewer.viewImage(ndarray, {
                  name: r.data.name.replace(".jpeg", "")
                });
              })
            );
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
    } /*
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
        },*/,
    async getStagePosition() {
      return axios.get(this.getPositionUri).then(r => r.data);
    },
    async setStagePosition(payload) {
      return axios.post(this.moveActionUri, payload).then(pollAction);
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
