<template>
  <div class="uk-flex uk-flex-center uk-flex-middle uk-margin">
    <div class="dpad-grid">
      <button
        id="up-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(0, 1, 0)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> arrow_upward </span>
      </button>

      <button
        id="left-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(-1, 0, 0)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> arrow_back </span>
      </button>

      <button
        id="right-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(1, 0, 0)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> arrow_forward </span>
      </button>

      <button
        id="down-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(0, -1, 0)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> arrow_downward </span>
      </button>

      <button
        id="focus-out-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(0, 0, -1)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> remove </span>
      </button>

      <button
        id="focus-in-button"
        class="uk-button uk-button-primary dpad-btn"
        @mousedown="jog(0, 0, 1)"
        @mouseup="jogStop()"
        @mouseOut="jogStop()"
      >
        <span class="material-symbols-outlined sync-icon"> add </span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "StageControlButtons",
  data: () => ({
    jogIntervalId: null,
    jogDistance: 600,
    jogTime: 300,
  }),
  methods: {
    jog(x, y, z) {
      if (this.jogIntervalId) {
        clearInterval(this.jogIntervalId);
      }
      let invokeJog = () =>
        this.invokeAction("stage", "jog", {
          x: x * this.jogDistance,
          y: y * this.jogDistance,
          z: z * this.jogDistance,
        });
      invokeJog();
      this.jogIntervalId = setInterval(invokeJog, this.jogTime);
    },
    jogStop() {
      if (this.jogIntervalId) {
        clearInterval(this.jogIntervalId);
      }
      this.invokeAction("stage", "jog", { stop: true });
    },
  },
};
</script>

<style scoped>
.dpad-grid {
  display: grid;
  grid-template-columns: repeat(3, 40px);
  grid-template-rows: 40px 40px 40px 20px 40px;
  gap: 1px;
  justify-content: center;
  align-items: center;
}

/* Place buttons within grid */
.dpad-grid #up-button {
  grid-column: 2;
  grid-row: 1;
}
.dpad-grid #left-button {
  grid-column: 1;
  grid-row: 2;
}
.dpad-grid #right-button {
  grid-column: 3;
  grid-row: 2;
}
.dpad-grid #down-button {
  grid-column: 2;
  grid-row: 3;
}
.dpad-grid #focus-out-button {
  grid-column: 1;
  grid-row: 5;
}
.dpad-grid #focus-in-button {
  grid-column: 3;
  grid-row: 5;
}

.dpad-btn {
  width: 40px;
  height: 40px;
  justify-content: center;
  align-items: center;
  display: flex;
}
</style>
