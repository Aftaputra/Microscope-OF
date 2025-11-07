<template>
  <div>
    <a class="uk-accordion-title" href="#">Configure</a>
    <div class="uk-accordion-content">
      <b>Keyboard Step Size</b>
      <div class="uk-grid-small uk-child-width-1-3" uk-grid>
        <div>
          <label class="uk-form-label" for="form-stacked-text">x</label>
          <div class="uk-form-controls">
            <input v-model="stepSize.x" class="uk-input uk-form-small" type="number" />
          </div>
          <label class="uk-margin-small-right"
            ><input v-model="invert.x" class="uk-checkbox" type="checkbox" /> Invert x</label
          >
        </div>

        <div>
          <label class="uk-form-label" for="form-stacked-text">y</label>
          <div class="uk-form-controls">
            <input v-model="stepSize.y" class="uk-input uk-form-small" type="number" />
          </div>
          <label class="uk-margin-small-right"
            ><input v-model="invert.y" class="uk-checkbox" type="checkbox" /> Invert y</label
          >
        </div>

        <div>
          <label class="uk-form-label" for="form-stacked-text">z</label>
          <div class="uk-form-controls">
            <input v-model="stepSize.z" class="uk-input uk-form-small" type="number" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SatgeControlSettings",

  computed: {
    // Note that as stepSize and invert are set based on internals we can use
    // get() and set() to interact with the store. Instead use a deep watcher to
    // update the store (see ``watch:`` below)
    stepSize() {
      return this.$store.state.navigationStepSize;
    },
    invert() {
      return this.$store.state.navigationInvert;
    },
  },

  watch: {
    stepSize: {
      deep: true,
      handler(newVal) {
        this.$store.commit("changeNavigationStepSize", newVal);
      },
    },
    invert: {
      deep: true,
      handler(newVal) {
        this.$store.commit("changeNavigationInvert", newVal);
      },
    },
  },
};
</script>
