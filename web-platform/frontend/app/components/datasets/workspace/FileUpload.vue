<template>
  <div>

    <div 
      class="file-upload-area"
      :class="{ 'dragover': isDragover }"
      @dragover.prevent="isDragover = true"
      @dragleave="isDragover = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        type="file"
        ref="fileInput"
        multiple
        @change="handleFileSelect"
        style="display: none"
      />
      
      <div class="upload-content">
        <v-icon size="48" color="primary">mdi-cloud-upload</v-icon>
        <p class="mt-2">{{ $t('fileupload.drag_and_drop') }}</p>
        <v-btn 
          color="primary" 
          variant="outlined"
          @click.stop="triggerFileInput"
          class="mt-2"
        >
          {{ $t('fileupload.browse_files') }}
        </v-btn>
      </div>
    </div>

    <div v-if="files.length > 0" class="files-info mt-4">
      <div class="files-summary">
        <div class="d-flex align-center justify-space-between">
          <span>{{ $t('fileupload.files') }} {{ files.length }}</span>

          <v-btn 
            size="small" 
            variant="text" 
            color="primary"
            @click.stop="showFilesList = !showFilesList"
          >
            {{ showFilesList ? $t('fileupload.hide') : $t('fileupload.show') }}
          </v-btn>
        </div>
      </div>

      <Transition name="slide-fade">
        <div v-if="showFilesList && files.length > 0" class="files-list">
          <div v-for="(file, index) in files" :key="index" class="file-item">
            <v-icon>mdi-file</v-icon>

            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">({{ formatFileSize(file.size) }})</span>

            <v-btn 
              icon 
              size="x-small" 
              variant="text"
              @click.stop="removeFile(index)"
              class="ml-2"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>
        </div>
      </Transition>
    </div>

    <Transition name="slide-fade">
      <div v-if="files.length > 0" class="metadata-form mt-6">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-information</v-icon>
            {{ $t('fileupload.metadata') }}
          </v-card-title>
          
          <v-card-text>
            <v-row>

              <v-col cols="12" md="6">
                <v-combobox
                  v-model="metadata.species"
                  :items="metadataOptions.species"
                  item-title="name"
                  item-value="id"
                  :label="$t('fileupload.species')"
                  variant="outlined"
                  clearable
                  :loading="loadingMetadata"
                >
                  <template #no-data>
                    <div class="pa-2">{{ $t('fileupload.select') }}</div>
                  </template>
                </v-combobox>
              </v-col>

              <v-col cols="12" md="6">
                <v-combobox
                  v-model="metadata.diagnosis"
                  :items="metadataOptions.diagnosis"
                  item-title="name"
                  item-value="id"
                  :label="$t('fileupload.diagnosis')"
                  variant="outlined"
                  clearable
                  :loading="loadingMetadata"
                >
                  <template #no-data>
                    <div class="pa-2">{{ $t('fileupload.select') }}</div>
                  </template>
                </v-combobox>
              </v-col>

              <v-col cols="12" md="6">
                <v-combobox
                  v-model="metadata.localization"
                  :items="metadataOptions.localizations"
                  item-title="name"
                  item-value="id"
                  :label="$t('fileupload.localization')"
                  variant="outlined"
                  clearable
                  :loading="loadingMetadata"
                >
                  <template #no-data>
                    <div class="pa-2">{{ $t('fileupload.select') }}</div>
                  </template>
                </v-combobox>
              </v-col>

              <v-col cols="12" md="6">
                <v-combobox
                  v-model="metadata.sex"
                  :items="metadataOptions.sex"
                  item-title="name"
                  item-value="id"
                  :label="$t('fileupload.sex')"
                  variant="outlined"
                  clearable
                  :loading="loadingMetadata"
                >
                  <template #no-data>
                    <div class="pa-2">{{ $t('fileupload.select') }}</div>
                  </template>
                </v-combobox>
              </v-col>

              <v-col cols="12">
                <div class="age-fields">
                  <div class="text-caption text-medium-emphasis mb-2">{{ $t('fileupload.age') }}</div>
                  <div class="d-flex gap-2" style="max-width: 400px;">
                    <v-text-field
                      v-model.number="metadata.ageYears"
                      :label="$t('fileupload.years')"
                      type="number"
                      variant="outlined"
                      clearable
                      min="0"
                      max="100"
                      class="age-field"
                    >
                      <template #append>
                        <span class="text-caption">{{ $t('fileupload.years_short') }}</span>
                      </template>
                    </v-text-field>
                    
                    <v-text-field
                      v-model.number="metadata.ageMonths"
                      :label="$t('fileupload.months')"
                      type="number"
                      variant="outlined"
                      clearable
                      min="0"
                      max="11"
                      class="age-field"
                    >
                      <template #append>
                        <span class="text-caption">{{ $t('fileupload.months_short') }}</span>
                      </template>
                    </v-text-field>
                  </div>
                </div>
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="metadata.weight"
                  :label="$t('fileupload.weight')"
                  type="number"
                  step="0.1"
                  variant="outlined"
                  clearable
                  style="max-width: 200px;"
                >
                  <template #append>
                    <span class="text-caption">{{ $t('fileupload.kg') }}</span>
                  </template>
                </v-text-field>
              </v-col>

            </v-row>
          </v-card-text>
        </v-card>

      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
const { t } = useI18n()
const { authGet} = useAuthFetch()
const fileInput = ref(null)
const isDragover = ref(false)
const files = ref([])
const showFilesList = ref(false)
const loadingMetadata = ref(false)
const metadataOptions = ref({
  species: [],
  diagnosis: [],
  localizations: [],
  sex: []
})

const metadata = ref({
  species: null,
  diagnosis: null,
  localization: null,
  sex: null,
  weight: null, 
  ageYears: 0,
  ageMonths: 0
})

const emit = defineEmits(['files-selected', 'files-updated', 'upload-start', 'upload-complete'])

onMounted(async () => {
  await loadMetadataOptions()
})

const loadMetadataOptions = async () => {
  try {
    loadingMetadata.value = true
    const response = await authGet('/api/assets/metadata/') 

    const transformArray = (arr, nameKey) => {
      if (!arr || !Array.isArray(arr)) return []
      return arr.map((item, index) => ({
        id: index + 1,
        name: item[nameKey] 
      }))
    }

    metadataOptions.value = {
      species: transformArray(response.Species?.species, 'species_name'),
      diagnosis: transformArray(response.Diagnosis?.diagnosis, 'diagnosis_name'),
      localizations: transformArray(response.Localization?.localizations, 'localization_name'),
      sex: transformArray(response.Sex?.sex, 'sex_name') 
    }
    
  } catch (error) {
    console.error('Error loading metadata options:', error)
  } finally {
    loadingMetadata.value = false
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  files.value = Array.from(event.target.files)
  emit('files-selected', files.value)
}

const handleDrop = (event) => {
  isDragover.value = false
  files.value = Array.from(event.dataTransfer.files)
  emit('files-selected', files.value)
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const removeFile = (index) => {
  files.value.splice(index, 1)
  emit('files-updated', files.value)
  
  if (files.value.length === 0) {
    showFilesList.value = false
  }
}

defineExpose({ metadata })
</script>

<style scoped>
.file-upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.file-upload-area.dragover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.upload-content {
  pointer-events: none;
}

.upload-content > * {
  pointer-events: auto;
}

.files-info {
  margin-top: 16px;
}

.files-list {
  margin-top: 8px;
  text-align: left;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border-bottom: 1px solid #eee;
}

.file-name {
  margin: 0 8px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #757575;
  font-size: 0.9em;
}

.metadata-form {
  border-top: 1px solid #eee;
  padding-top: 16px;
}

.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

.gap-2 {
  gap: 8px;
}
</style>