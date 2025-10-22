<!--
  This is a temporary holidng file for content that needs to be put into the new
  structure
-->
<div v-show="stepValue == 0">
        
      </div>

      <div v-show="stepValue == 1">
        <h3>Lens-shading</h3>
        <div v-if="isLSTCalibrated">
          <p>
            <b
              >Your lens-shading table has already been calibrated. Click Next
              to move on.</b
            >
          </p>
        </div>
        <div v-else>
          

          <miniStreamDisplay
            v-if="stepValue == 1"
            class="mini-preview"
          ></miniStreamDisplay>

          <p>Once you're ready, click auto-calibrate.</p>

          <cameraCalibrationSettings
            :show-extra-settings="false"
            :camera-uri="cameraUri"
          ></cameraCalibrationSettings>
        </div>
      </div>

      <div v-show="stepValue == 2">
        <h3>Adjust z height</h3>
        <p>
          Insert a sample and adjust the z position of 
          the stage using the buttons below, until the 
          sample is in focus.
        </p>
        <p>
          You may also adjust the z position with <b>page up</b> and <b>page down</b>.
        </p>

        <miniStreamDisplay
          v-if="stepValue == 2"
          class="mini-preview"
        ></miniStreamDisplay>
        <div class="action-button-container">
          <action-button
          class="moveZ"
          thing="stage"
          action="move_relative"
          :button-primary="false"
          :submit-data="{ x: 0, y: 0, z: -100}"
          :submit-label="' - '"
          :hideOnRun="false"
          :can-terminate="false"
          />
          <action-button
          class="moveZ"
          thing="stage"
          action="move_relative"
          :button-primary="false"
          :submit-data="{ x: 0, y: 0, z: 100}"
          :submit-label="'+'"
          :can-terminate="false"
          :hideOnRun="false"
          />
        </div>
      </div>

      <div v-show="stepValue == 3">
        <h3>Camera-stage mapping</h3>
        <div v-if="isCSMCalibrated">
          <p>
            <b
              >Your camera-stage mapping has already been calibrated. Click Next
              to move on.</b
            >
          </p>
        </div>
        <div v-else-if="!canCSMCalibrated">
          <p>
            <b
              >No stage connected. Please skip this step, or connect a valid
              stage, then reboot your microscope.</b
            >
          </p>
        </div>
        <div v-else>
          <p>
            <b
              >Follow the important steps below before starting camera-stage
              mapping calibration!</b
            >
          </p>
          <ul class="uk-list uk-list-bullet">
            <li>Insert a clearly visible sample to the microscope</li>
            <li>
              Ensure the sample is reasonably well centered on the microscope
              camera
            </li>
          </ul>

          <miniStreamDisplay
            v-if="stepValue == 3"
            class="mini-preview"
          ></miniStreamDisplay>

          <p>Once you're ready, click auto-calibrate.</p>

          <CSMCalibrationSettings
            :show-extra-settings="false"
          ></CSMCalibrationSettings>
        </div>
      </div>

      <div v-show="stepValue == 4">
        <p>
          <b>Calibration complete</b>
        </p>
        <p>
          Click Finish to return to your microscope, or Restart to re-run the
          calibration routine
        </p>
      </div>

<script>
import cameraCalibrationSettings from "../tabContentComponents/settingsComponents/cameraSettingsComponents/cameraCalibrationSettings.vue";
import CSMCalibrationSettings from "../tabContentComponents/settingsComponents/CSMSettingsComponents/CSMCalibrationSettings.vue";
import miniStreamDisplay from "../genericComponents/miniStreamDisplay.vue";


export default {
  name: "calibrationWizard",

  components: {
    cameraCalibrationSettings,
    CSMCalibrationSettings,
    miniStreamDisplay,
    ActionButton
  },
}
</script>
<style scoped>

.action-button-container {
  display: flex;
  flex-direction: row;   /* Stack vertically */
  justify-content: center;  /* Left align */
  gap: 8px;                  /* Small space between buttons */
  margin-top: 4px;           /* Gap from image */
}
>>> .moveZ .uk-button.uk-width-1-1 {
  line-height: 50px;
  font-size: 50px !important;
  height: 60px; 
  padding-bottom: 46px;
  margin: 0;                 /* Remove default margin */
  width: 120px;
  min-width: 80px;
}
</style>
