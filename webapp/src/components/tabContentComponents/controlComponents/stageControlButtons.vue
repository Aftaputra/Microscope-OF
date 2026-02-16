<template>
  <div class="uk-flex uk-flex-center uk-flex-middle uk-margin">
    <div class="dpad-grid">
      <button id="up-button" class="uk-button uk-button-primary dpad-btn" @click="move(0, 1, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_upward </span>
      </button>

      <button id="left-button" class="uk-button uk-button-primary dpad-btn" @click="move(-1, 0, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_back </span>
      </button>

      <button id="right-button" class="uk-button uk-button-primary dpad-btn" @click="move(1, 0, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_forward </span>
      </button>

      <button id="down-button" class="uk-button uk-button-primary dpad-btn" @click="move(0, -1, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_downward </span>
      </button>

      <button
        id="focus-out-button"
        class="uk-button uk-button-primary dpad-btn"
        @click="move(0, 0, -1)"
      >
        <span class="material-symbols-outlined sync-icon"> remove </span>
      </button>

      <button
        id="focus-in-button"
        class="uk-button uk-button-primary dpad-btn"
        @click="move(0, 0, 1)"
      >
        <span class="material-symbols-outlined sync-icon"> add </span>
      </button>
    </div>
  </div>
</template>

<script>
import { eventBus } from "../../../eventBus.js";

export default {
  name: "StageControlButtons",
  methods: {
    move(x, y, z) {
      eventBus.emit("globalMoveStepEvent", { x, y, z, absolute: false });
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
