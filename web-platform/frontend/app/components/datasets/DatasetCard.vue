<template>
  <v-card 
    class="dataset-card" 
    :class="[viewMode === 'list' ? 'list-card' : 'grid-card', { 'hover-card': !loading }]"
    elevation="3"
  >
    <template v-if="viewMode === 'grid'">
      <div v-if="dataset.last_image" class="image-container" @click="openDataset">
        <img :src="dataset.last_image" :alt="dataset.dataset_name" class="image" />
        <div class="image-overlay"></div>
      </div>

      <div v-else class="image-placeholder" @click="openDataset">
        <v-icon size="64" color="grey-lighten-2">mdi-image-off</v-icon>
      </div>

      <v-card-item @click="openDataset">
        <div class="d-flex justify-space-between align-start mb-3">
          <div class="d-flex align-center flex-grow-1 min-width-0">
            <v-icon color="primary" size="32" class="mr-3 flex-shrink-0">mdi-database</v-icon>
            <div class="min-width-0">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props: tooltipProps }">
                  <v-card-title 
                    ref="titleRef"
                    class="text-h6 font-weight-medium pa-0 text-truncate"
                    v-bind="tooltipProps"
                  >
                    {{ getDatasetNameWithoutId(dataset.dataset_name, dataset.dataset_id) }}
                  </v-card-title>
                </template>
                <span>{{ getDatasetNameWithoutId(dataset.dataset_name, dataset.dataset_id) }}</span>
              </v-tooltip>

              <v-chip
                :color="dataset.access_type === 'Public' ? 'success' : 'primary'"
                variant="outlined"
                size="small"
                class="mt-1"
              >
                {{ dataset.access_type === 'Public' ? $t('datasets.filter_public') : $t('datasets.filter_private') }}
              </v-chip>
            </div>
          </div>
        </div>
      </v-card-item>
    </template>

    <template v-else>
      <div class="list-content">
        <div class="list-image" @click="openDataset">
          <img v-if="dataset.last_image" :src="dataset.last_image" :alt="dataset.dataset_name" />
          <v-icon v-else size="48" color="grey-lighten-2">mdi-image-off</v-icon>
        </div>
        
        <div class="list-info flex-grow-1 min-width-0" @click="openDataset">
          <v-tooltip location="bottom">
          <template v-slot:activator="{ props: tooltipProps }">
            <v-card-title 
              ref="titleRef"
              class="text-h6 pa-0 text-truncate"
              v-bind="tooltipProps"
            >
              {{ getDatasetNameWithoutId(dataset.dataset_name, dataset.dataset_id) }}
            </v-card-title>
          </template>
          <span>{{ getDatasetNameWithoutId(dataset.dataset_name, dataset.dataset_id) }}</span>
          </v-tooltip>

          <v-chip
            :color="dataset.access_type === 'Public' ? 'success' : 'primary'"
            variant="outlined"
            size="small"
            class="mt-1"
          >
            {{ dataset.access_type === 'Public' ? $t('datasets.filter_public') : $t('datasets.filter_private') }}
          </v-chip>
        </div>
      </div>
    </template>
  </v-card>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const props = defineProps({
  dataset: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  viewMode: {
    type: String,
    default: 'grid'
  }
})
const emit = defineEmits(['edit-metadata', 'edit-users'])

const getDatasetNameWithoutId = (datasetName, datasetId) => {
  const datasetIdStr = `${datasetId}`
  if (datasetName.startsWith(`${datasetIdStr}_`)) {
    return datasetName.slice(datasetIdStr.length + 1)
  }
  return datasetName
}

const openDataset = () => {
  router.push(`/dataset/${props.dataset.dataset_id}`)
}

</script>

<style scoped>
.grid-card {
  height: 100%;
  transition: all 0.3s ease;
  cursor: pointer;
}

.grid-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15) !important;
}

.image-container {
  position: relative;
  height: 180px;
  overflow: hidden;
  cursor: pointer;
}

.image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.3));
}

.image-placeholder {
  height: 180px;
  background: rgba(var(--v-theme-background), 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.admin-actions {
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

.grid-card:hover .admin-actions {
  opacity: 1;
}

:deep(.v-card-item) {
  padding: 16px !important;
  cursor: pointer;
}

.min-width-0 {
  min-width: 0;
}

.flex-grow-1 {
  flex-grow: 1;
}

.flex-shrink-0 {
  flex-shrink: 0;
}

.list-card {
  transition: all 0.3s ease;
  cursor: pointer;
}

.list-card:hover {
  transform: translateX(4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15) !important;
}

.list-content {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
}

.list-image {
  width: 60px;
  height: 60px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(var(--v-theme-background), 0.1);
  cursor: pointer;
}

.list-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.list-info {
  min-width: 0;
  cursor: pointer;
}

.list-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

.list-card:hover .list-actions {
  opacity: 1;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  position: relative;
}

.text-truncate:hover::after {
  content: attr(title);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  white-space: nowrap;
  z-index: 1000;
  pointer-events: none;
}

.admin-actions .v-btn:hover,
.list-actions .v-btn:hover {
  background: rgba(var(--v-theme-secondary), 0.1) !important;
  transform: scale(1.1);
}

</style>