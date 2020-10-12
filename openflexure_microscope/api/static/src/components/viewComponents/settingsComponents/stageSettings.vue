<template>
    <div id="stageSettings">
        <div>
            <h3>Stage settings</h3>
            <p>
                <label>
                    Stage Type
                    <div v-if="this.stageType != 'MissingStage'">
                        <form>
                            <div>
                                <select v-model="stageType" class="uk-select">
                                    <option value="SangaStage">SangaStage (Standard)</option>
                                    <option value= "SangaDeltaStage"> SangaStage (Delta)</option>
                                </select>
                            </div>
                            <div>
                                <taskSubmitter
                                    :can-terminate="false"
                                    :submit-url= "this.stageTypeUri"
                                    :submit-data="{'stage_type' : this.stageType}"
                                    :submit-label="'Change stage type'"
                                    @response="onStageTypeResponse"
                                    @error="onStageTypeError"
                                >
                            </div>
                        </form>   
                    </div>
                    <div v-else class="uk-text-danger"><b>No stage connected</b></div>
                </label>
            </p>
        </div>
    </div>
</template>

<script>

import axios from "axios";
import taskSubmitter from "../../genericComponents/taskSubmitter";

export default {
    name: "StageSettings",

    components:{
        taskSubmitter
    },

    data: function(){
        return {
            stageType: "MissingStage",
        }
    },
    
    computed: {
        stageTypeUri: function() {
        return `${this.$store.getters.baseUri}/api/v2/actions/stage/type`;
        },
    },

    mounted(){
        this.getStageType();
    },

    methods: {
        getStageType: function(){
            console.log("Getting stage type")
            axios
                .get(this.stageTypeUri)
                .then(response => {
                    console.log("Stage type is " + response.data.stage_type)
                    this.stageType = response.data.stage_type;
                })
                .catch(error => {
                    this.modalError(error);
                });
        },
        onStageTypeResponse: function(response) {
            this.modalNotify("Stage type changed.");
            console.log("Stage type changed to " + response.output.stage_type)
            this.stageType = response.output.stage_type
        },

        onStageTypeError: function(error) {
        this.modalError(error); // Let mixin handle error
        }
    }
}
</script>

<style lang="less"></style>
