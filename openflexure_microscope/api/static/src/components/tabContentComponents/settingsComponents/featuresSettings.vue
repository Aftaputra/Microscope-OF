<template>
  <div id="appSettings" class="uk-width-large">
    <h3>Additional features</h3>
    <p class="uk-margin-small">
      <label
        ><input v-model="IHIEnabled" class="uk-checkbox" type="checkbox" />
        Enable IHI Slide Scan</label
      >
    </p>
    <p class="uk-margin-small">
      Enabling IHI Slide Scan will add a new tab designed to simplify acquiring
      blood smear tile scans. <br />
      While this may be useful for other applications, it is primarily designed
      for use in clinics acquiring blood smear samples using a 100x
      oil-immersion objective, with a Raspberry Pi Camera v2.
    </p>
    <p class="uk-margin-small" :class="{'uk-text-muted': !imjoyPermitted}">
      <label :disabled="!imjoyPermitted">
        <input v-model="imjoyEnabled" class="uk-checkbox" type="checkbox" :disabled="!imjoyPermitted"/>
        Enable ImJoy plugin engine
      </label>
    </p>
    <p class="uk-margin-small" v-if="imjoyPermitted">
      <a href="https://imjoy.io/">ImJoy</a> enables integration with a wide
      variety of microscopy and image analysis applications, including ImageJ.JS
      and Kaibu. Support for ImJoy within the OFM software is currently
      experimental, and it may slow down loading of the application.
    </p>
    <p class="uk-margin-small uk-text-muted" v-if="!imjoyPermitted">
      ImJoy plugins are disabled in this build of the OpenFlexure software.
    </p>
    <p class="uk-margin-small">
      <label
        ><input v-model="galleryEnabled" class="uk-checkbox" type="checkbox" />
        Enable Gallery</label
      >
    </p>
    <p class="uk-margin-small">
      The "gallery" tab can cause performance issues; un-tick the box above to
      disable it.
    </p>
  </div>
</template>

<script>
// Export main app
export default {
  name: "FeaturesSettings",

  data: function() {
    return {};
  },

  computed: {
    IHIEnabled: {
      get() {
        return this.$store.state.IHIEnabled;
      },
      set(value) {
        this.$store.commit("changeIHIEnabled", value);
      }
    },
    imjoyEnabled: {
      get() {
        return this.$store.state.imjoyEnabled;
      },
      set(value) {
        this.$store.commit("changeImjoyEnabled", value);
      }
    },
    galleryEnabled: {
      get() {
        return this.$store.state.galleryEnabled;
      },
      set(value) {
        this.$store.commit("changeGalleryEnabled", value);
      }
    },
    imjoyPermitted: function () {
      // ImJoy may be disabled using an environment variable.
      // If this function returns false, it is never possible to
      // use ImJoy, so we should gray out the option.
      return process.env.VUE_APP_ENABLE_IMJOY === "true";
    }
  },

  watch: {
    IHIEnabled: function() {
      this.setLocalStorageObj("IHIEnabled", this.IHIEnabled);
    },
    imjoyEnabled: function() {
      this.setLocalStorageObj("imjoyEnabled", this.imjoyEnabled);
    },
    galleryEnabled: function() {
      this.setLocalStorageObj("galleryEnabled", this.galleryEnabled);
    }
  },

  mounted() {
    // Try loading settings from localStorage. If null, don't change.
    this.IHIEnabled = this.getLocalStorageObj("IHIEnabled") || this.IHIEnabled;
    this.imjoyEnabled =
      this.getLocalStorageObj("imjoyEnabled") || this.imjoyEnabled;
    this.galleryEnabled =
      this.getLocalStorageObj("galleryEnabled") || this.galleryEnabled;
  }
};
</script>

<style lang="less"></style>
