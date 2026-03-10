<template>
  <!-- Workflow Selection Dropdown -->
  <div ref="slideScanControls" class="uk-margin">
    <label class="uk-form-label">Workflow</label>

    <select
      class="uk-select uk-form-small"
      :value="workflowName"
      @change="setWorkflow($event.target.value)"
    >
      <option v-for="(label, name) in workflowOptions" :key="name" :value="name">
        {{ label }}
      </option>
    </select>
  </div>
  <server-specified-interface :elements="workflowSettings" @request-update="readSettings" />
  <ul uk-accordion="multiple: true">
    <li class="uk-open">
      <a class="uk-accordion-title" href="#">Stitching Settings</a>
      <div class="uk-accordion-content">
        <div class="uk-margin">
          <propertyControl
            thing-name="smart_scan"
            property-name="stitch_automatically"
            label="Automatically Stitch Images Together"
          />
        </div>
        <div class="uk-margin">
          <propertyControl
            thing-name="smart_scan"
            property-name="stitch_tiff"
            label="When Stitching, Produce a Pyramidal TIFF"
          />
        </div>
      </div>
    </li>
  </ul>
</template>

<script>
import propertyControl from "@/components/labThingsComponents/propertyControl.vue";
import ServerSpecifiedInterface from "@/components/labThingsComponents/serverSpecifiedInterface.vue";
import { useIntersectionObserver } from "@vueuse/core";

export default {
  name: "SlideScanControls",

  components: {
    propertyControl,
    ServerSpecifiedInterface,
  },

  data() {
    return {
      workflowName: undefined,
      workflowSettings: [],
      workflowOptions: [],
    };
  },

  async created() {
    this.readSettings();
    this.workflowOptions = await this.readThingProperty(
      "smart_scan",
      "workflow_display_names",
      true,
    );
  },

  mounted() {
    // sets visibilityChanged to true or false, which can then update settings if needed
    useIntersectionObserver(
      this.$refs.slideScanControls,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0,
      },
    );
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.readSettings();
      }
    },
    async readSettings() {
      this.workflowName = await this.readThingProperty("smart_scan", "workflow_name");

      if (!this.workflowName) {
        console.warn("Could not read workflow_name, using default");
        this.workflowName = "histo_scan_workflow";
      }

      if (this.workflowName) {
        this.ready = await this.readThingProperty(this.workflowName, "ready", true);
        this.workflowSettings =
          (await this.getThingEndpoint(this.workflowName, "settings_ui")) || [];
      }
    },
    async setWorkflow(name) {
      try {
        this.workflowName = name;

        await this.writeThingProperty("smart_scan", "workflow_name", name);

        // refresh  UI
        await this.readSettings();
      } catch (err) {
        this.modalError(err);

        // revert if server rejected
        this.workflowName = await this.readThingProperty("smart_scan", "workflow_name", true);
      }
    },
  },
};
</script>

<style scoped></style>
