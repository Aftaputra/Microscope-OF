<template>
    <div id="stageSettings">
        <div>
            <h3>Stage settings</h3>
            <p>
                <label>
                    Stage Type
                    <div v-if="this.stageType != 'MissingStage'">
                        <select v-model="stageType" class="uk-select">
                            <option value="SangaStage">SangaStage (Standard)</option>
                            <option value= "SangaDeltaStage"> SangaStage (Delta)</option>
                        </select>
                    </div>
                    <div v-else class="uk-text-danger"><b>No stage connected</b></div>
                </label>
            </p>
        </div>
    </div>
</template>

<script>

import axios from "axios";

export default {
    name: "StageSettings",

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

    watch:{
        stageType: function(){
            this.setStageType();
        }
    },

    methods: {
        getStageType: function(){
            console.log("Getting stage type")
            axios
                .get(this.stageTypeUri)
                .then(response => {
                    console.log("Stage type is " + response.data)
                    this.stageType = response.data;
                })
                .catch(error => {
                    this.modalError(error);
                });
        },
        setStageType: function(){
            console.log("Changing stage type")
            axios
                .post(this.stageTypeUri,{"stage_type" : this.stageType})
                .then(response => {
                    console.log("Stage type changed")
                })
                .catch(error => {
                    this.modalError(error);
                });
        }
    }
}
</script>

<style lang="less"></style>
