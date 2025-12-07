<template>
  <v-container fluid class="pa-0">

    <v-toolbar color="surface" density="comfortable">

      <v-btn icon @click="$router.push('/datasets')" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
        <v-tooltip activator="parent" location="bottom">{{ $t('dataset.back_to_datasets') }}</v-tooltip>
      </v-btn>

      <v-toolbar-title class="text-h6">
        {{ datasetNameWithoutId || $t('dataset.loading') }}
      </v-toolbar-title>

      <div class="d-flex align-center">
        <v-chip 
          :color="getStatusColor(dataset?.status)" 
          size="small" 
          variant="outlined"
          class="mr-2"
          >
          {{ getStatusText(dataset?.status) }}
        </v-chip>
      </div>

      <v-btn color="primary" variant="outlined" class="mr-2" @click="runModel('TRAIN')"  :disabled="!is_admin && !is_editor"
            v-tooltip="{ location: 'bottom', text: $t('dataset.start_train') }">
        <v-icon left>mdi-brain</v-icon>
      </v-btn>

      <v-btn color="secondary" variant="outlined" class="mr-2 " @click="runModel('INFERENCE')" :disabled="!is_admin && !is_editor"
            v-tooltip="{ location: 'bottom', text: $t('dataset.start_inference') }">
        <v-icon left>mdi-robot</v-icon>
      </v-btn>

      <v-select
        :model-value="annotationMode"
        @update:model-value="setAnnotationMode"
        :items="modeItems"
        variant="outlined"
        density="comfortable"
        class="mr-2 mode-select action-height"
        style="width: auto; display: inline-flex; flex: 0 auto"
        hide-details
        >

        <template v-slot:selection="{ item }">
          <v-icon :icon="item.raw.icon" size="small" class="mr-2"></v-icon>
          <span class="d-none d-sm-inline">{{ item.raw.title }}</span>
        </template>
        
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props">
            <template v-slot:prepend>
              <v-icon :icon="item.raw.icon" class="mr-2"></v-icon>
            </template>
          </v-list-item>
        </template>

      </v-select>

      
      <v-tabs v-model="currentTab">
        <v-tab value="workspace" v-tooltip="{ location: 'bottom', text: $t('dataset.workspace') }">
          <v-icon left>mdi-view-dashboard</v-icon>
        </v-tab>
        
        <v-tab value="info" v-tooltip="{ location: 'bottom', text: $t('dataset.menegment')}">
          <v-icon left>mdi-information</v-icon>
        </v-tab>
      </v-tabs>

    </v-toolbar>

    <v-window v-model="currentTab">
      <v-window-item value="workspace">
        <WorkspaceView 
        ref="workspaceViewRef"
          :datasetId="datasetId" 
          :annotationMode="annotationMode"
          :lableProperties="lableProperties"
          :favoriteClasses="favoriteClasses"
          :is_admin="is_admin"
          :is_editor="is_editor"
        />
      </v-window-item>
      
      <v-window-item value="info">
        <DatasetManagement 
          :datasetId="datasetId" 
          :dataset="dataset"
          @assets-updated="fetchDataset"
        />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
definePageMeta({
  requiresAuth: true,
})
import WorkspaceView from '@/components/datasets/workspace/WorkspaceView.vue'
import DatasetManagement from '@/components/datasets/DatasetManagement/DatasetManagement.vue'
import { useRoute } from 'vue-router'
import { useAnnotationModeStore } from '@/stores/annotationMode'

const { t } = useI18n()
const workspaceViewRef = ref(null)
const { authGet, authPost } = useAuthFetch()
const is_admin = ref(false)
const is_editor = ref(false)
const route = useRoute()
const dataset = ref(null)
const currentTab = ref('workspace')
const modeItems = [
  { value: 'detection', title: t('dataset.detection'), icon: 'mdi-vector-square' },
  { value: 'segmentation', title: t('dataset.segmentation'), icon: 'mdi-brush' }
]
const annotationModeStore = useAnnotationModeStore()
const annotationMode = computed(() => annotationModeStore.mode)
const setAnnotationMode = annotationModeStore.setMode
const lableProperties = ref([])
const favoriteClasses = ref([])
const datasetId = computed(() => route.params.id)
const { status: wsStatus, message: wsMessage, isConnected } = useDatasetWebSocket(datasetId.value)
const datasetNameWithoutId = computed(() => {
  if (!dataset.value || !dataset.value.dataset_name) {
    return ''
  }
  
  const datasetIdStr = `${datasetId.value}`
  
  if (dataset.value.dataset_name.startsWith(`${datasetIdStr}_`)) {
    return dataset.value.dataset_name.slice(datasetIdStr.length + 1)
  }
  
  return dataset.value.dataset_name
})
watch(wsStatus, (newStatus) => {
  if (newStatus && dataset.value) {
    dataset.value.status = newStatus
  }
}, { immediate: true })

const getStatusColor = (status) => {
  const statusColors = {
    'FREE': '#28a745',
    'TRAINING': 'rgb(215, 122, 60)',
    'INFERENCE': 'blue',
    'UPLOAD': 'rgb(225, 38, 172)',
    'CREATE DATASET': 'rgb(24, 199, 226)',
    'DOWNLOAD': 'rgb(255, 149, 0)'
  }
  return statusColors[status] || 'grey'
}

const getStatusText = (status) => {
  return status 
}

const runModel = async (task) => {
  try {
    const formData = new FormData()
    formData.append('mode',  annotationMode.value.charAt(0).toUpperCase() + annotationMode.value.slice(1))
    formData.append('task', task)
    await authPost(`/api/dataset/${datasetId.value}/packages/`, formData)
  } catch (error) {
    console.error('Error running model:', error)
  }
}

const fetchDataset = async () => {
  try {
    const response = await authGet(`/api/datasets/${datasetId.value}/`)
    dataset.value = response.dataset
    is_admin.value = response.is_admin
    is_editor.value = response.is_editor
    lableProperties.value = dataset.value?.label_properties || []
    favoriteClasses.value = dataset.value?.favorites_labels || []
    workspaceViewRef.value.handleDeleteUpdate()
  } catch (error) {
    console.error('Error fetching dataset:', error)
    navigateTo('/')
  }
}

onMounted(() => {
  annotationModeStore.initialize()
  fetchDataset()
})

watch(datasetId, fetchDataset)

</script>

<style scoped>
.mode-select {
  min-width: 140px;
}

.action-height {
  min-height: 48px; 
  height: 48px;
  display: flex;
  align-items: center;
}

</style>