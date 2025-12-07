<template>
  <v-container fluid class="py-6">
    <v-card-actions class="pt-0 px-0" v-if="datasetData">
      <v-btn color="primary" @click="fetchDataset">
        <v-icon left>mdi-refresh</v-icon>
       {{ $t('datasetmanagement.refresh') }}
      </v-btn>
      <div class="simple-copy">
        <v-btn 
          variant="outlined" 
          color="secondary" 
          @click="startCopy"
          :disabled="isCopying"
          :loading="isCopying"
        >
          <v-icon left>mdi-content-copy</v-icon>
         {{ $t('datasetmanagement.copy') }}
        </v-btn>


        <v-dialog v-model="showCopyDialog" max-width="400" persistent>
          <v-card>
            <v-card-title class="text-h6">
              {{ $t('datasetmanagement.copy') }}
            </v-card-title>
            
            <v-card-text>
              <div v-if="!copyStarted">
               
                <v-text-field
                  v-model="copyDatasetName"
                  :label="$t('datasetmanagement.copy_name')"
                  :placeholder="datasetNameWithoutId + '_copy'"
                  class="mb-4"
                />
                
                <v-checkbox
                  v-model="copyWithAnnotations"
                  :label="$t('datasetmanagement.copy_annotations')"
                  color="primary"
                  hide-details
                />
              </div>

              <div v-else class="text-center">
                
                <div v-if="!copyCompleted">
                  <v-progress-circular
                    :size="50"
                    :width="5"
                    :model-value="copyProgress"
                    color="primary"
                    class="mb-4"
                  >
                    {{ copyProgress }}%
                  </v-progress-circular>
                  
                  <p class="mb-2">{{ $t('datasetmanagement.copying') }}</p>
                  
                </div>
                
                <!-- Завершено -->
                <div v-if="copyCompleted">
                  <v-icon color="success" size="48" class="mb-2">mdi-check-circle</v-icon>
                  <p>{{ $t('datasetmanagement.copied') }}</p>
                  <p class="text-caption text-grey">{{ $t('datasetmanagement.newdatasetcreate') }}</p>
                </div>
              </div>
            </v-card-text>

            <v-card-actions>
              <v-spacer></v-spacer>
               <v-btn 
                    v-if="!copyStarted"
                    color="grey" 
                    variant="text"
                    @click="closeCopyDialog"
                >
                    {{ $t('datasetmanagement.cancel') }}
                </v-btn>
              <v-btn 
                v-if="!copyStarted"
                color="primary" 
                @click="confirmCopy"
                :disabled="!copyDatasetName"
              >
                {{ $t('datasetmanagement.copy') }}
              </v-btn>
              <v-btn 
                v-if="copyCompleted"
                color="primary" 
                @click="closeCopyDialog"
              >
                {{ $t('datasetmanagement.close') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </div>
       <div class="simple-export">
          
          <v-btn 
            variant="outlined" 
            color="secondary" 
            @click="startExport"
            :disabled="isExporting"
            :loading="isExporting"
          >
            <v-icon left>mdi-download</v-icon>
           {{ $t('datasetmanagement.export') }}
          </v-btn>

         
          <v-dialog v-model="showStatus" max-width="400" persistent>
            <v-card>
              <v-card-title class="text-h6">
                {{ $t('datasetmanagement.archive') }}
              </v-card-title>
              
              <v-card-text>
                <div class="text-center">
                  
                  <div v-if="!exportCompleted">
                    <v-progress-circular
                      :size="50"
                      :width="5"
                      :model-value="exportProgress"
                      color="primary"
                      class="mb-4"
                    >
                      {{ exportProgress }}%
                    </v-progress-circular>
                    
                    <p class="mb-2">{{ $t('datasetmanagement.archiving') }}</p>
                    
                  </div>
                  
            
                  <div v-if="exportCompleted">
                    <v-icon color="success" size="48" class="mb-2">mdi-check-circle</v-icon>
                    <p>{{ $t('datasetmanagement.archived') }}</p>
                    <p class="text-caption text-grey">{{ $t('datasetmanagement.startdownload') }}</p>
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-dialog>
        </div>

      <v-spacer></v-spacer> 

     <v-btn 
        v-if ="datasetData.is_admin || datasetData.is_editor"
        color="error" 
        variant="text" 
        @click="confirmDeleteDatasetDialog = true"
      >
        <v-icon left>mdi-delete</v-icon>
        {{ $t('datasetmanagement.deletedataset') }}
      </v-btn>

      
      <v-dialog v-model="confirmDeleteDatasetDialog" max-width="500">
        <v-card>
          <v-card-title class="text-h5">
            <v-icon color="error" class="mr-2">mdi-alert</v-icon>
           {{ $t('datasetmanagement.confirmdeletetitle') }}
          </v-card-title>
          
          <v-card-text>
            {{ $t('datasetmanagement.confirmdelete') }} "<strong>{{ datasetData.name }}</strong>"?
            <br><br>
            <span class="text-error">{{ $t('datasetmanagement.warning') }}</span>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn 
              color="grey" 
              variant="text" 
              @click="confirmDeleteDatasetDialog = false"
            >
              {{ $t('datasetmanagement.cancel') }}
            </v-btn>
            <v-btn 
              color="error" 
              variant="elevated" 
              @click="deleteDataset"
              :loading="deleteLoading"
            >
              <v-icon left>mdi-delete</v-icon>
              {{ $t('datasetmanagement.delete') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card-actions>
    <v-row>
      <v-col cols="12">
        <v-card v-if="loading" class="pa-6">
          <v-skeleton-loader type="card, actions"></v-skeleton-loader>
        </v-card>

        <v-alert v-else-if="error" type="error">
          {{ error }}
        </v-alert>

        <template v-else-if="datasetData">
          <v-row align="stretch">
            <v-col cols="12" md="6">
              <v-card class="pa-4" style="height: 100%;">
                <v-card-title>{{ $t('datasetmanagement.datasetinfo') }}</v-card-title>
                <v-list lines="two">
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-identifier</v-icon>
                    </template>
                    <v-list-item-title>ID</v-list-item-title>
                    <v-list-item-subtitle>{{ datasetData.dataset.dataset_id }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-rename-box</v-icon>
                    </template>
                    <v-list-item-title>{{ $t('datasetmanagement.name') }}</v-list-item-title>
                    <v-list-item-subtitle>{{ datasetNameWithoutId }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-shield-account</v-icon>
                    </template>
                    <v-list-item-title>{{ $t('datasetmanagement.owner') }}</v-list-item-title>
                    <v-list-item-subtitle>
                      <v-chip :color="datasetData.dataset.access_type === 'Public' ? 'success' : 'primary'" size="small">
                        {{ datasetData.dataset.access_type === 'Public' ? 'Public' : 'Private' }}
                      </v-chip>
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-account-key</v-icon>
                    </template>
                    <v-list-item-title>{{ $t('datasetmanagement.role') }}</v-list-item-title>
                    <v-list-item-subtitle>
                      <v-chip :color="datasetData.is_admin ? 'orange' : datasetData.is_editor ? 'blue' : 'grey'" size="small">
                          <v-icon left small>
                            {{ datasetData.is_admin ? 'mdi-shield-crown' : datasetData.is_editor ? 'mdi-pencil' : 'mdi-account' }}
                          </v-icon>
                          {{ datasetData.is_admin ? $t('datasetmanagement.admin') : datasetData.is_editor ? $t('datasetmanagement.editor') : $t('datasetmanagement.user') }}
                        </v-chip>
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>

            <v-col cols="12" md="6">
              <v-card class="pa-4" style="height: 100%;">
                <v-card-title class="d-flex align-center">
                  <v-icon class="mr-2">mdi-chart-box</v-icon>
                  {{ $t('datasetmanagement.statistics') }}
                </v-card-title>
   
                <v-list-item class="border-b mb-2">
                  <template v-slot:prepend>
                    <v-icon color="primary" class="mr-3">mdi-database</v-icon>
                  </template>
                  
                  <v-list-item-title class="font-weight-bold">{{ $t('datasetmanagement.records') }}</v-list-item-title>
                  
                  <template v-slot:append>
                    <span class="text-h5 text-primary">{{ totalRecords }}</span>
                  </template>
                </v-list-item>

                <v-table density="comfortable">
                  <thead>
                    <tr>
                      <th class="text-left">{{ $t('datasetmanagement.type') }}</th>
                      <th class="text-center">{{ $t('datasetmanagement.count') }}</th>
                      <th class="text-center">{{ $t('datasetmanagement.validated') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <div class="d-flex align-center">
                          <v-icon color="purple" class="mr-2">mdi-brush</v-icon>
                          <span>{{ $t('datasetmanagement.segmentation') }}</span>
                        </div>
                      </td>
                      <td class="text-center">
                        <strong class="text-purple">{{ totalSegmentationCount }}</strong>
                      </td>
                      <td class="text-center">
                        <v-chip size="small" :color="totalValidationMaskCount === totalSegmentationCount ? 'green' : 'orange'" variant="outlined">
                          {{ totalValidationMaskCount }}
                        </v-chip>
                      </td>
                    </tr>
                    
                    <tr>
                      <td>
                        <div class="d-flex align-center">
                          <v-icon color="blue" class="mr-2">mdi-vector-square</v-icon>
                          <span>{{ $t('datasetmanagement.detection') }}</span>
                        </div>
                      </td>
                      <td class="text-center">
                        <strong class="text-blue">{{ totalDetectionCount }}</strong>
                      </td>
                      <td class="text-center">
                        <v-chip size="small" :color="totalValidationBboxCount === totalDetectionCount ? 'green' : 'orange'" variant="outlined">
                          {{ totalValidationBboxCount }}
                        </v-chip>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card>
            </v-col>
          </v-row>

         
          <v-card class="mt-4">
            <v-tabs v-model="currentTab" bg-color="surface">
              <v-tab value="assets">
                <v-icon left>mdi-folder-image</v-icon>
                {{ $t('datasetmanagement.assets') }}
                <v-chip size="x-small" class="ml-2">{{ datasetData.assets?.length || 0 }}</v-chip>
              </v-tab>
              
              <v-tab value="classes">
                <v-icon left>mdi-tag-multiple</v-icon>
                {{ $t('datasetmanagement.classes') }}
                <v-chip size="x-small" class="ml-2">{{ Object.keys(datasetData.dataset.label_properties).length || 0 }}</v-chip>
              </v-tab>
              
              <v-tab value="metadata">
                <v-icon left>mdi-database-cog</v-icon>
                {{ $t('datasetmanagement.metadata') }}
              </v-tab>
              
              <v-tab value="users" v-if="datasetData.is_admin">
                <v-icon left>mdi-account-group</v-icon>
                {{ $t('datasetmanagement.users') }}
                <v-chip size="x-small" class="ml-2">{{ userStats.length }}</v-chip>
              </v-tab>
            </v-tabs>

            <v-window v-model="currentTab">
              <v-window-item value="assets">
                <div class="pa-4">
                  <div class="d-flex justify-space-between align-center mb-4">
                    <v-card-title class="pa-0">{{ $t('datasetmanagement.assets') }}</v-card-title>
                    
                  </div>

                  <v-data-table
                    :headers="assetHeaders"
                    :items="datasetData.assets"
                    :items-per-page="10"
                    class="elevation-1"
                    >
                    <template v-slot:item.asset_name="{ item }">
                      <div class="d-flex align-center">
                        <v-icon class="mr-2">mdi-file-image</v-icon>
                        {{ item.asset_name }}
                      </div>
                    </template>

                    <template v-slot:item.records_count="{ item }">
                      <v-chip size="small" :color="getColorByCount(item.records_count)">
                        {{ item.records_count }} 
                      </v-chip>
                    </template>

                    <template v-slot:item.segmentation_count="{ item }">
                      <v-chip size="small" :color="getColorByCount(item.segmentation_count, item.records_count)" variant="outlined">
                        {{ item.segmentation_count }}
                      </v-chip>
                    </template>

                    <template v-slot:item.detection_count="{ item }">
                      <v-chip size="small" :color="getColorByCount(item.detection_count, item.records_count)" variant="outlined">
                        {{ item.detection_count }}
                      </v-chip>
                    </template>

                    <template v-slot:item.validation_mask_count="{ item }">
                      <v-chip 
                        size="small" 
                        :color="item.validation_mask_count === item.records_count ? 'green' : 'orange'"
                        variant="flat"
                      >
                        {{ item.validation_mask_count }}/{{ item.records_count }}
                      </v-chip>
                    </template>

                    <template v-slot:item.validation_bbox_count="{ item }">
                      <v-chip 
                        size="small" 
                        :color="item.validation_bbox_count === item.records_count ? 'green' : 'orange'"
                        variant="flat"
                      >
                        {{ item.validation_bbox_count }}/{{ item.records_count }}
                      </v-chip>
                    </template>

                    <template v-slot:item.actions="{ item }">
                      <v-dialog v-model="item.deleteDialog" max-width="400">
                        <template v-slot:activator="{ props: activatorProps }">
                          <v-btn 
                            :disabled="!datasetData.is_admin && !datasetData.is_editor"
                            icon 
                            size="small" 
                            color="error"
                            v-bind="activatorProps"
                            :title=" $t('datasetmanagement.deleteasset') "
                          >
                            <v-icon>mdi-delete</v-icon>
                          </v-btn>
                        </template>
    
                        <v-card>
                          <v-card-title>{{ $t('datasetmanagement.confirmdeletetitle') }}</v-card-title>
                          <v-card-text>
                            {{ $t('datasetmanagement.confirmdeletetext') }} "{{ item.asset_name }}"?
                        
                          </v-card-text>
                          <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn @click="item.deleteDialog = false">{{ $t('datasetmanagement.cancel') }}</v-btn>
                            <v-btn color="error" @click="deleteAsset(item)">{{ $t('datasetmanagement.delete') }}</v-btn>
                          </v-card-actions>
                        </v-card>
                      </v-dialog>
                    </template>
                  </v-data-table>
                </div>
              </v-window-item>

              
              <v-window-item value="classes">
                <div class="pa-4">
                  <v-card-title class="pa-0 mb-4">{{ $t('datasetmanagement.statistics') }}</v-card-title>
                  
                  <v-card variant="outlined" class="mb-4">
                    <v-tabs v-model="classStatsLevel" color="primary">
                      <v-tab value="dataset">{{ $t('datasetmanagement.statisticsdataset') }}</v-tab>
                      <v-tab value="assets">{{ $t('datasetmanagement.statisticsassets') }}</v-tab>
                      <v-tab value="records">{{ $t('datasetmanagement.statisticsrecords') }}</v-tab>
                    </v-tabs>
                  </v-card>

                  <div v-if="classStatsLevel === 'dataset'">
                    <div class="d-flex align-center gap-4 mb-4">
                      <span class="text-body-1 font-weight-medium">{{ $t('datasetmanagement.sort') }}</span>
                      <div class="d-flex align-center gap-2">
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('detection_count')"
                          :color="sortConfig.field === 'detection_count' ? 'primary' : undefined"
                          class="px-3"
                          >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'detection_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-bar' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.detection') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('segmentation_count')"
                          :color="sortConfig.field === 'segmentation_count' ? 'primary' : undefined"
                          class="px-3"
                          >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'segmentation_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-pie' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.segmentation') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('label_name')"
                          :color="sortConfig.field === 'name' ? 'primary' : undefined"
                          class="px-3"
                          >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'name' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-alphabetical' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.forname') }}
                        </v-btn>
                      </div>
                    </div>
                    <v-row>
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="primary" class="mr-2">mdi-chart-bar</v-icon>
                            {{ $t('datasetmanagement.detection') }} 
                          </v-card-title>
                          <v-card-text>
                            <div v-for="classItem in datasetClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                  
                                  <span class="text-caption text-medium-emphasis">
                                  {{ classItem.detection_count }}({{ classItem.detection_percentage.toFixed(2) }}%)
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.detection_percentage" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                      
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="green" class="mr-2">mdi-chart-pie</v-icon>
                            {{ $t('datasetmanagement.segmentation') }} 
                          </v-card-title>
                          <v-card-text>
                          <div v-for="classItem in datasetClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                  
                                    <span class="text-caption text-medium-emphasis">
                                    {{ classItem.segmentation_count.toFixed(2) }}%
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.segmentation_count" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                    </v-row>
                  </div>

                  <div v-else-if="classStatsLevel === 'assets'">
                    <div class="d-flex align-center gap-4 mb-4">
                      <span class="text-body-1 font-weight-medium">{{ $t('datasetmanagement.sort') }}</span>
                      <div class="d-flex align-center gap-2">
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('detection_count')"
                          :color="sortConfig.field === 'detection_count' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'detection_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-bar' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.detection') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('segmentation_count')"
                          :color="sortConfig.field === 'segmentation_count' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'segmentation_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-pie' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.segmentation') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('label_name')"
                          :color="sortConfig.field === 'name' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'name' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-alphabetical' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.forname') }}
                        </v-btn>
                      </div>
                    </div>
                    <v-select
                      v-model="classselectedAsset"
                      :items="datasetData.assets"
                      :item-title="item => item.asset_name"
                      item-value=""
                      :label="$t('datasetmanagement.selectasset')"
                      class="mb-4"
                      clearable
                      return-object
                    >
                      <template #item="{ props, item }">
                        <v-list-item v-bind="props" :title="item.raw.asset_name"></v-list-item>
                      </template>
                    </v-select>
      
                    <v-row v-if="classselectedAsset">
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="primary" class="mr-2">mdi-chart-bar</v-icon>
                            {{ $t('datasetmanagement.detection') }} 
                          </v-card-title>
                          <v-card-text>
                            <div v-for="classItem in assetClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                  
                                  <span class="text-caption text-medium-emphasis">
                                {{ classItem.detection_count }}({{ classItem.detection_percentage.toFixed(2) }}%)
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.detection_percentage" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                      
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="green" class="mr-2">mdi-chart-pie</v-icon>
                            {{ $t('datasetmanagement.segmentation') }}
                          </v-card-title>
                          <v-card-text>
                          <div v-for="classItem in assetClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                  
                                    <span class="text-caption text-medium-emphasis">
                                    {{ classItem.segmentation_count.toFixed(2) }}%
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.segmentation_count" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                    </v-row>
                  </div>

                  <div v-else-if="classStatsLevel === 'records'">
                    <div class="d-flex align-center gap-4 mb-4">
                      <span class="text-body-1 font-weight-medium">{{ $t('datasetmanagement.sort') }}</span>
                      <div class="d-flex align-center gap-2">
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('detection_count')"
                          :color="sortConfig.field === 'detection_count' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'detection_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-bar' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.detection') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('segmentation_count')"
                          :color="sortConfig.field === 'segmentation_count' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'segmentation_count' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-chart-pie' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.segmentation') }}
                        </v-btn>
                        
                        <v-btn 
                          size="small" 
                          variant="outlined"
                          @click="setSort('label_name')"
                          :color="sortConfig.field === 'name' ? 'primary' : undefined"
                          class="px-3"
                        >
                          <template #prepend>
                            <v-icon size="small">
                              {{ sortConfig.field === 'name' ? 
                                  (sortConfig.direction === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 
                                  'mdi-alphabetical' }}
                            </v-icon>
                          </template>
                          {{ $t('datasetmanagement.forname') }}
                        </v-btn>
                      </div>
                    </div>
                    <v-select
                      v-model="classselectedRecord"
                      :items="datasetData.records"
                      :item-title="item => getRecordName(item.record_link)" 
                      item-value=""
                      :label="$t('datasetmanagement.selectrecord')"
                      class="mb-4"
                      clearable
                      return-object
                      >
                      <template #item="{ props, item }">
                        <v-list-item v-bind="props" :title="getRecordName(item.raw.record_link)"></v-list-item>
                      </template>
                    </v-select>
        
                    <v-row v-if="classselectedRecord">
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="primary" class="mr-2">mdi-chart-bar</v-icon>
                            {{ $t('datasetmanagement.detection') }} 
                          </v-card-title>
                          <v-card-text>
                            <div v-for="classItem in recordClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                
                                  <span class="text-caption text-medium-emphasis">
                                  {{ classItem.detection_count }}({{ classItem.detection_percentage.toFixed(2) }}%)
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.detection_percentage" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                      
                      <v-col cols="12" md="6">
                        <v-card variant="outlined">
                          <v-card-title class="d-flex align-center">
                            <v-icon color="green" class="mr-2">mdi-chart-pie</v-icon>
                            {{ $t('datasetmanagement.segmentation') }} 
                          </v-card-title>
                          <v-card-text>
                          <div v-for="classItem in recordClassStats" :key="classItem.label_name" class="mb-3">
                              <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center">
                                  <v-icon :color="classItem.color" size="small" class="mr-2">mdi-circle</v-icon>
                                  <span class="text-caption">{{ classItem.display_name }}</span>
                                </div>
                                <div class="d-flex align-center gap-2">
                                  
                                    <span class="text-caption text-medium-emphasis">
                                    {{ classItem.segmentation_count.toFixed(2) }}%
                                  </span>
                                </div>
                              </div>
                              <v-progress-linear 
                                :model-value="classItem.segmentation_count" 
                                :color="classItem.color"
                                height="6"
                                rounded
                              ></v-progress-linear>
                            </div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                    </v-row>
                  </div>
                </div>
              </v-window-item>

              <v-window-item value="metadata">
                <div class="pa-4">
                  <div class="d-flex justify-space-between align-center mb-4">
                    <v-card-title class="pa-0">{{ $t('datasetmanagement.metadata') }}</v-card-title>
                    <v-btn color="primary" variant="outlined" size="small" @click="editMetadata" v-if="datasetData.is_admin || datasetData.is_editor">
                      <v-icon left>mdi-pencil</v-icon>
                      {{ $t('datasetmanagement.edit') }}
                    </v-btn>
                  </div>

                  <v-card v-if="metadataLoading" class="pa-4">
                    <v-skeleton-loader type="list-item-two-line, list-item-two-line, list-item-two-line"></v-skeleton-loader>
                  </v-card>

       
                  <v-alert v-else-if="metadataError" type="error" class="mb-4">
                    {{ metadataError }}
                  </v-alert>

                  <template v-else-if="metadataData">
                    <v-card variant="outlined" class="mb-4">
                      <v-card-text>
                        <v-list lines="two">
                  
                          <v-list-item>
                            <template v-slot:prepend>
                              <v-icon>mdi-devices</v-icon>
                            </template>
                            <v-list-item-title>{{ $t('datasetmanagement.devicetype') }}</v-list-item-title>
                            <v-list-item-subtitle>
                              <v-chip v-if="metadataData.device_type" size="small" color="primary">
                                {{ metadataData.device_type }}
                              </v-chip>
                              <span v-else class="text-grey">{{ $t('datasetmanagement.unknown') }}</span>
                            </v-list-item-subtitle>
                          </v-list-item>

                          <v-list-item>
                            <template v-slot:prepend>
                              <v-icon>mdi-scale</v-icon>
                            </template>
                            <v-list-item-title>{{ $t('datasetmanagement.scalingvalue') }}</v-list-item-title>
                            <v-list-item-subtitle>
                              <v-chip v-if="metadataData.scaling_value" size="small" color="secondary">
                                {{ metadataData.scaling_value }}
                              </v-chip>
                              <span v-else class="text-grey">{{ $t('datasetmanagement.unknown') }}</span>
                            </v-list-item-subtitle>
                          </v-list-item>

                          <v-list-item>
                            <template v-slot:prepend>
                              <v-icon>mdi-ruler</v-icon>
                            </template>
                            <v-list-item-title>{{ $t('datasetmanagement.scales') }}</v-list-item-title>
                            <v-list-item-subtitle>
                              <div v-if="metadataData.scales && metadataData.scales.length > 0" class="d-flex flex-wrap gap-1">
                                <v-chip 
                                  v-for="(scale, index) in metadataData.scales" 
                                  :key="index" 
                                  size="small" 
                                  variant="outlined"
                                  @click="editScale(index)"
                                >
                                  {{ formatScale(scale) }}
                                </v-chip>
                              </div>
                              <span v-else class="text-grey">{{ $t('datasetmanagement.unknown') }}</span>
                            </v-list-item-subtitle>
                          </v-list-item>

                        
                        </v-list>
                      </v-card-text>
                    </v-card>
                    <v-alert v-if="!hasMetadata" type="info">
                      {{ $t('datasetmanagement.no_metadata') }}
                    </v-alert>
                  </template>
                </div>

                <v-dialog v-model="arbitraryDataDialog" max-width="800px">
                  <v-card>
                    <v-card-title>{{ $t('datasetmanagement.arbitrarydata') }}</v-card-title>
                    <v-card-text>
                      <pre class="json-view">{{ JSON.stringify(metadataData?.arbitrary_data, null, 2) }}</pre>
                    </v-card-text>
                    <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn @click="arbitraryDataDialog = false">{{ $t('datasetmanagement.close') }}</v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>

                <v-dialog v-model="editMetadataDialog" max-width="600px" :persistent="savingMetadata" @click:outside="closeEditDialog">
                  <v-card>
                    <v-card-title>{{ $t('datasetmanagement.edit') }}</v-card-title>
                    <v-card-text>
                      <v-form v-model="metadataFormValid" ref="metadataForm">
                        <v-combobox
                          v-model="editForm.device_type"
                          :items="metadataData?.device_types || []"
                          item-title="device_type_name"
                          item-value="device_type_name"
                          :label="$t('datasetmanagement.devicetype')"
                          clearable
                        >
                          <template v-slot:item="{ props, item }">
                            <v-list-item v-bind="props">
                              <template v-slot:title>
                                {{ item.raw.device_type_name }}
                              </template>
                            </v-list-item>
                          </template>
                        </v-combobox>

                        <v-combobox
                          v-model="editForm.scaling_value"
                          :items="metadataData?.scaling_values || []"
                          item-title="scaling_value_name"
                          item-value="scaling_value_name"
                          :label="$t('datasetmanagement.scalingvalue')"
                          clearable
                        >
                          <template v-slot:item="{ props, item }">
                            <v-list-item v-bind="props">
                              <template v-slot:title>
                                {{ item.raw.scaling_value_name }}
                              </template>
                            </v-list-item>
                          </template>
                        </v-combobox>

                        <div class="mb-4">
                          <div class="d-flex justify-space-between align-center mb-2">
                            <label class="v-label">{{ $t('datasetmanagement.scales') }}</label>
                            <v-btn size="small" color="primary" variant="outlined" @click="addNewScaleDirect">
                              <v-icon left>mdi-plus</v-icon>
                              {{ $t('datasetmanagement.add') }}
                            </v-btn>
                          </div>
                          
                          <v-card variant="outlined" v-if="editForm.scales.length > 0" class="pa-3">
                            <v-row v-for="(scale, sIndex) in editForm.scales" :key="sIndex" class="mb-2 align-center">
                              <v-col cols="3">
                                <v-text-field 
                                  v-model.number="scale.barcode" 
                                  label="Barcode" 
                                  type="number" 
                                  variant="outlined"
                                  min="0"
                                />
                              </v-col>
                              <v-col cols="3">
                                <v-select 
                                  v-model="scale.unit" 
                                  :items="['nm','µm','mm','m']" 
                                  label="Unit" 
                                  variant="outlined" 
                                />
                              </v-col>
                              <v-col cols="3">
                                <v-text-field 
                                  v-model.number="scale.value_per_pixel" 
                                  label="Value per Pixel" 
                                  type="number" 
                                  variant="outlined"
                                  step="0.01"
                                  min="0.01"
                                />
                              </v-col>
                              <v-col cols="3" class="d-flex align-center">
                                <v-btn icon color="red" @click="removeScaleDirect(sIndex)" size="small">
                                  <v-icon>mdi-delete</v-icon>
                                </v-btn>
                              </v-col>
                            </v-row>
                          </v-card>
                          
                          <v-alert v-else type="info" density="compact">
                            {{ $t('datasetmanagement.no_scales') }}
                          </v-alert>
                        </div>

                        <v-file-input
                          v-model="labelsFile"
                          accept=".json,.yaml,.yml,.txt"
                          label="Files (JSON/YAML)"
                          prepend-icon="mdi-file-upload"
                          variant="outlined"
                          @click:clear="clearLabelsFile"
                        ></v-file-input>
                        
                      </v-form>
                    </v-card-text>
                    <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn @click="editMetadataDialog = false" variant="text">{{ $t('datasetmanagement.cancel') }}</v-btn>
                      <v-btn 
                        color="primary" 
                        @click="saveMetadata" 
                        :loading="savingMetadata"
                      >
                        {{ $t('datasetmanagement.save') }}
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </v-window-item>

              <v-window-item value="users">
                <div class="pa-4">
                  <div class="d-flex justify-space-between align-center mb-4">
                    <v-card-title class="pa-0">{{ $t('datasetmanagement.users') }}</v-card-title>
                    <v-btn color="primary" variant="outlined" size="small" @click="addUserDialog = true">
                      <v-icon left>mdi-account-plus</v-icon>
                      {{ $t('datasetmanagement.add') }}
                    </v-btn>
                  </div>

                  <v-card v-if="usersLoading" class="pa-4">
                    <v-skeleton-loader type="table-row@3"></v-skeleton-loader>
                  </v-card>


                  <v-alert v-else-if="usersError" type="error" class="mb-4">
                    {{ usersError }}
                  </v-alert>


                  <v-data-table
                    v-else
                    :headers="userHeaders"
                    :items="userStats"
                    :items-per-page="10"
                    class="elevation-1"
                  >
                    <template v-slot:item.user="{ item }">
                      <div class="d-flex align-center">
                        <v-avatar size="32" class="mr-2" color="primary" variant="tonal">
                          <v-icon>mdi-account</v-icon>
                        </v-avatar>
                        {{ item.username }}
                      </div>
                    </template>

                    <template v-slot:item.role="{ item }">
                      <v-chip :color="getRoleColor(item.role)" size="small">
                        {{ getRoleText(item.role) }}
                      </v-chip>
                    </template>

                    <template v-slot:item.actions="{ item }">
                      <v-btn 
                        v-if="item.role !== 'Admin'" 
                        icon 
                        size="small" 
                        color="error" 
                        :title="$t('datasetmanagement.remove_user')"
                        @click="removeUser(item)"
                        :loading="removingUserId === item.user_id"
                      >
                        <v-icon>mdi-delete</v-icon>
                      </v-btn>
                      <v-icon v-else color="grey">mdi-lock</v-icon>
                    </template>

                    <template v-slot:no-data>
                      <div class="text-center py-4">
                        <v-icon size="64" color="grey">mdi-account-multiple</v-icon>
                        <div class="text-h6 mt-2">{{ $t('datasetmanagement.no_users') }}</div>
                        
                      </div>
                    </template>
                  </v-data-table>
                </div>

               
              </v-window-item>

              <v-dialog v-model="addUserDialog" max-width="500px">
                <v-card>
                  <v-card-title>{{ $t('datasetmanagement.add_user') }}</v-card-title>
                  <v-card-text>
                    <v-form v-model="addUserFormValid" ref="addUserForm">
                      <v-text-field
                        v-model="newUser.username"
                        :label="$t('datasetmanagement.username')"
                        :rules="[v => !!v]"
                        required
                      ></v-text-field>
                      
                      <v-select
                        v-model="newUser.role"
                        :items="availableRoles"
                        :label="$t('datasetmanagement.role')"
                        :rules="[v => !!v]"
                        required
                      ></v-select>
                    </v-form>
                  </v-card-text>
                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn @click="addUserDialog = false" variant="text">{{ $t('datasetmanagement.cancel') }}</v-btn>
                    <v-btn 
                      color="primary" 
                      @click="addUser" 
                      :loading="addingUser"
                      :disabled="!addUserFormValid"
                    >
                      {{ $t('datasetmanagement.add') }}
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <v-dialog v-model="confirmDeleteDialog" max-width="400px">
                <v-card>
                  <v-card-title class="text-h6">{{ $t('datasetmanagement.confirmdeletetitle') }}</v-card-title>
                  <v-card-text>
                    {{ $t('datasetmanagement.confirmdeletetext') }}
                    <strong>{{ userToDelete?.username }}</strong> 
                  </v-card-text>
                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn 
                      @click="confirmDeleteDialog = false" 
                      variant="text"
                      :disabled="removingUserId !== null"
                    >
                      {{ $t('datasetmanagement.cancel') }}
                    </v-btn>
                    <v-btn 
                      color="error" 
                      @click="confirmDelete" 
                      :loading="removingUserId !== null"
                      variant="flat"
                    >
                      {{ $t('datasetmanagement.delete') }}
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>
            </v-window>
          </v-card>
        </template>
      </v-col>
    </v-row>

    
  </v-container>
</template>


<script setup>

import { useRouter } from 'vue-router'
const props = defineProps({
  datasetId: {
    type: String,
    required: true
  }
})
const emit = defineEmits(['assets-updated'])
const { t } = useI18n()
const router = useRouter()
const { authGet, authDelete, authPost, authUpload } = useAuthFetch()

const datasetData = ref(null)
const loading = ref(true)
const error = ref('')
const currentTab = ref('assets')
const assetMetadataDialog = ref(false)
const selectedAsset = ref(null)



const metadataData = ref(null)
const metadataLoading = ref(false)
const metadataError = ref('')
const arbitraryDataDialog = ref(false)

const editMetadataDialog = ref(false)
const metadataFormValid = ref(false)
const metadataForm = ref(null)
const savingMetadata = ref(false)
const arbitraryDataError = ref('')

const labelsFile = ref(null)
const showStatus = ref(false)
const isExporting = ref(false)
const exportProgress = ref(0)
const exportFilesProcessed = ref(0)
const exportFilesTotal = ref(0)
const exportCompleted = ref(false)

const startExport = async () => {
  isExporting.value = true
  showStatus.value = true
  exportProgress.value = 0
  exportCompleted.value = false

  try {
  
    const response = await authPost(`/api/datasets/${props.datasetId}/download/`, {
    })

    const downloadId = response.download_id

  
    const checkStatus = async () => {
      try {
        const status = await authGet(`/api/downloads/${downloadId}/status/`)
        

        exportProgress.value = status.progress
        exportFilesProcessed.value = status.files_uploaded
        exportFilesTotal.value = status.total_files_expected


        if (status.status === 'completed') {
          exportCompleted.value = true
          
   
          setTimeout(() => {
       
            if (status.download_url) {
              window.open(status.download_url, '_blank')
            }
            

            showStatus.value = false
            isExporting.value = false
          }, 1500)
          
          return true
        }


        if (status.status === 'failed') {

          showStatus.value = false
          isExporting.value = false
  
          return true
        }

        return false

      } catch (error) {
       
        return true 
      }
    }


    const pollInterval = setInterval(async () => {
      const shouldStop = await checkStatus()
      if (shouldStop) {
        clearInterval(pollInterval)
      }
    }, 2000)

  } catch (error) {

    showStatus.value = false
    isExporting.value = false
  }
}


watch(showStatus, (newVal) => {
  if (!newVal && isExporting.value) {

    isExporting.value = false
  }
})
const deleteAsset = async (asset) => {
 
    try {
    
      await authDelete(`/api/assets/${asset.asset_id}/`)

      const index = datasetData.value.assets.findIndex(a => a.asset_id === asset.asset_id)
      if (index !== -1) {
        datasetData.value.assets.splice(index, 1)
      }
      fetchDataset()
      emit('assets-updated')
      
    } catch (error) {
      console.error('Error deleting asset:', error)
    
    }
  
}

const showCopyDialog = ref(false)
const isCopying = ref(false)
const copyStarted = ref(false)
const copyCompleted = ref(false)
const copyProgress = ref(0)
const copyFilesProcessed = ref(0)
const copyFilesTotal = ref(0)
const copyDatasetName = ref('')
const copyWithAnnotations = ref(true)

const startCopy = () => {
  showCopyDialog.value = true
  copyDatasetName.value = datasetNameWithoutId.value + '_copy'
  copyWithAnnotations.value = true
  copyStarted.value = false
  copyCompleted.value = false
  copyProgress.value = 0
}

const datasetNameWithoutId = computed(() => {
  console.log('datasetData.dataset', datasetData.value.dataset)
  if (!datasetData.value.dataset || !datasetData.value.dataset.dataset_name) {
    return ''
  }
  console.log('datasetData.dataset.dataset_name', datasetData.value.dataset.dataset_name)
  const datasetIdStr = `${props.datasetId}`
  
  if (datasetData.value.dataset.dataset_name.startsWith(`${datasetIdStr}_`)) {
    return datasetData.value.dataset.dataset_name.slice(datasetIdStr.length + 1)
  }
  
  return datasetData.value.dataset.dataset_name
})

const confirmCopy = async () => {
  isCopying.value = true
  copyStarted.value = true

  try {

    const response = await authPost(`/api/copy_dataset/${props.datasetId}/`, {
     
        dataset_name: copyDatasetName.value,
        records_validation: copyWithAnnotations.value
    
    })

    const downloadId = response.download_id


    const pollCopyStatus = async () => {
      try {
        const status = await authGet(`/api/downloads/${downloadId}/status/`)
        
        copyProgress.value = status.progress
        copyFilesProcessed.value = status.files_uploaded
        copyFilesTotal.value = status.total_files_expected

        if (status.status === 'completed') {
          copyCompleted.value = true
          isCopying.value = false
          return true
        }

        if (status.status === 'failed') {
          
          isCopying.value = false
          return true
        }

        return false

      } catch (error) {
        
        return true
      }
    }

    const copyInterval = setInterval(async () => {
      const shouldStop = await pollCopyStatus()
      if (shouldStop) {
        clearInterval(copyInterval)
      }
    }, 2000)

  } catch (error) {

    isCopying.value = false
  }
}

const closeCopyDialog = () => {
  if (copyCompleted.value){
    navigateTo('datasets/')
  }
  showCopyDialog.value = false
  isCopying.value = false
  copyStarted.value = false
  copyCompleted.value = false

  
}
const loadJsonFromUrl = async (url) => {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
  
    return null
  }
}

const getRecordName = (url) => {
  if (!url) return ''
  const path = url.split('?')[0]
  return path.split('/').pop() 
}


const clearLabelsFile = () => {
  labelsFile.value = null
}

const addNewScaleDirect = () => {
  if (!editForm.value.scales) {
    editForm.value.scales = []
  }
  editForm.value.scales.push({
    unit: '',
    barcode: '',
    value_per_pixel: ''
  })
}

const removeScaleDirect = (index) => {
  editForm.value.scales.splice(index, 1)
}

const editForm = ref({
  device_type: '',
  scaling_value: '',
  scales: [],
  arbitrary_data_json: ''
})


const hasMetadata = computed(() => {
  return metadataData.value && (
    metadataData.value.device_type || 
    metadataData.value.scaling_value || 
    metadataData.value.scales?.length > 0 ||
    metadataData.value.arbitrary_data
  )
})



const formatScale = (scale) => {
  if (typeof scale === 'string') return scale
  return `(${scale.value_per_pixel}${scale.unit}/px)${scale.barcode ? `, barcode ${scale.barcode}${scale.unit} ` : ''}`
}


const fetchMetadata = async () => {
  metadataLoading.value = true
  metadataError.value = ''
  
  try {
    const response = await authGet(`/api/dataset/metadata_static/${props.datasetId}/`)
    metadataData.value = response
  } catch (err) {
  
    metadataError.value = 'Error'
  } finally {
    metadataLoading.value = false
  }
}

const editMetadata = () => {
  editForm.value = {
    device_type: metadataData.value?.device_type || '',
    scaling_value: metadataData.value?.scaling_value || '',
    scales: metadataData.value?.scales ? [...metadataData.value.scales] : [],
    arbitrary_data_json: metadataData.value?.arbitrary_data ? 
      JSON.stringify(metadataData.value.arbitrary_data, null, 2) : ''
  }
  arbitraryDataError.value = ''
  clearLabelsFile()
  editMetadataDialog.value = true
}

const saveMetadata = async () => {
  savingMetadata.value = true
  try {
    const formData = new FormData()
    
 
    formData.append('device_type',JSON.stringify({'device_type_name': editForm.value.device_type.device_type_name || ''}))
    formData.append('scaling_value',JSON.stringify({'scaling_value_name': editForm.value.scaling_value.scaling_value_name || ''}))
    formData.append('scales', JSON.stringify(editForm.value.scales))


    if (labelsFile.value) {
      formData.append('label_properties', labelsFile.value)
    }

    const response = await authUpload(`/api/dataset/metadata_static/${props.datasetId}/`, formData)

    fetchMetadata()
    editMetadataDialog.value = false
    
  } catch (error) {
 
  } finally {
    savingMetadata.value = false
  }
}
const closeEditDialog = () => {
  if (!savingMetadata.value) {
    editMetadataDialog.value = false
  }
}


watch(currentTab, (newTab) => {
  if (newTab === 'metadata' && !metadataData.value) {
    fetchMetadata()
  }
})



const classStatsLevel = ref('dataset')
const classStats = ref([])
const assetClassStatsdata = ref({})

const sortConfig = ref({
  field: 'detection_count', 
  direction: 'desc' 
})

const classselectedAsset = ref(null)
const classselectedRecord = ref(null)
const recordClassStatsdata = ref({})

watch(classselectedRecord, async () => {

  if (!classselectedRecord.value) return

  recordClassStatsdata.value.detection = await loadJsonFromUrl(classselectedRecord.value.detection_metrics)
  recordClassStatsdata.value.segmentation = await loadJsonFromUrl(classselectedRecord.value.segmentation_metrics)
}, { immediate: true, deep: true })


watch(classselectedAsset, async () => {

  if (!classselectedAsset.value) return
  assetClassStatsdata.value = await loadJsonFromUrl(classselectedAsset.value.metrics)
}, { immediate: true, deep: true })


const recordClassStats = computed(() => {
  
  if (!recordClassStatsdata.value || Object.keys(recordClassStatsdata.value).length === 0) {
    return []
  }

  const detectionData = recordClassStatsdata.value.detection || {}
  const segmentationData = recordClassStatsdata.value.segmentation || {}

  const formattedStats = Array.from(Object.keys(datasetData.value.dataset.label_properties)).map(className => {
  
    const color = datasetData.value.dataset.label_properties[className]
    
    return {
      label_name: className,
      display_name: className, 
      color: color,
      detection_count: detectionData[className] || 0,
      segmentation_count: segmentationData[className] || 0,
      detection_percentage: detectionData[className] ? 
        (detectionData[className] / Object.values(detectionData).reduce((a, b) => a + b, 0)) * 100 : 0,
      
    }
  })
  const sorted = [...formattedStats].sort((a, b) => {
    let aValue = a[sortConfig.value.field]
    let bValue = b[sortConfig.value.field]
    
    if (typeof aValue === 'string') {
      return aValue.localeCompare(bValue)
    }
    
    return aValue - bValue
  })

  return sortConfig.value.direction === 'desc' ? sorted.reverse() : sorted
})


const assetClassStats = computed(() => {


  if (!assetClassStatsdata.value || Object.keys(assetClassStatsdata.value).length === 0) {
    return []
  }

  const detectionData = assetClassStatsdata.value.detection || {}
  const segmentationData = assetClassStatsdata.value.segmentation.total_square || {}


  const formattedStats = Array.from(Object.keys(datasetData.value.dataset.label_properties)).map(className => {

    const color = datasetData.value.dataset.label_properties[className]
    
    return {
      label_name: className,
      display_name: className, 
      color: color,
      detection_count: detectionData[className] || 0,
      segmentation_count: segmentationData[className] || 0,
      detection_percentage: detectionData[className] ? 
        (detectionData[className] / Object.values(detectionData).reduce((a, b) => a + b, 0)) * 100 : 0,
      
    }
  })
  const sorted = [...formattedStats].sort((a, b) => {
    let aValue = a[sortConfig.value.field]
    let bValue = b[sortConfig.value.field]
    

    if (typeof aValue === 'string') {
      return aValue.localeCompare(bValue)
    }
    
  
    return aValue - bValue
  })


  return sortConfig.value.direction === 'desc' ? sorted.reverse() : sorted
})


const datasetClassStats = computed(() => {
  if (!classStats.value || Object.keys(classStats.value).length === 0) {
    return []
  }

  const detectionData = classStats.value.detection || {}
  const segmentationData = classStats.value.segmentation.total_square || {}
  const detection_percentage = classStats.value.detection_percentage || {}

  const formattedStats = Array.from(Object.keys(datasetData.value.dataset.label_properties)).map(className => {

    const color = datasetData.value.dataset.label_properties[className]
    
    return {
      label_name: className,
      display_name: className, 
      color: color,
      detection_count: detectionData[className] || 0,
      segmentation_count: segmentationData[className] || 0,
      detection_percentage: detection_percentage[className] || 0,
      
    }
  })
  const sorted = [...formattedStats].sort((a, b) => {
    let aValue = a[sortConfig.value.field]
    let bValue = b[sortConfig.value.field]
    

    if (typeof aValue === 'string') {
      return aValue.localeCompare(bValue)
    }
    

    return aValue - bValue
  })

  return sortConfig.value.direction === 'desc' ? sorted.reverse() : sorted
})
const setSort = (field) => {
  if (sortConfig.value.field === field) {

    sortConfig.value.direction = sortConfig.value.direction === 'asc' ? 'desc' : 'asc'
  } else {

    sortConfig.value.field = field
    sortConfig.value.direction = 'desc'
  }
}


const userStats = ref([])
const usersLoading = ref(false)
const usersError = ref('')
const removingUserId = ref(null)
const addingUser = ref(false)


const addUserDialog = ref(false)
const addUserFormValid = ref(false)
const newUser = ref({
  username: '',
  role: 'Viewer'
})


const userHeaders = [
  { title: $t('datasetmanagement.username'), key: 'username' },
  { title: $t('datasetmanagement.role'), key: 'role', align: 'center' },
  { title: $t('datasetmanagement.actions'), key: 'actions', align: 'end', sortable: false }
]


const availableRoles = [
  { title: $t('datasetmanagement.editor'), value: 'Editor' },
  { title: $t('datasetmanagement.user'), value: 'Viewer' }
]


const getRoleColor = (role) => {
  switch (role) {
    case 'Admin': return 'orange'
    case 'Editor': return 'primary' 
    case 'Viewer': return 'green'
    default: return 'grey'
  }
}

const getRoleText = (role) => {
  switch (role) {
    case 'Admin': return $t('datasetmanagement.admin')
    case 'Editor': return $t('datasetmanagement.editor')
    case 'Viewer': return $t('datasetmanagement.user')
    default: return role
  }
}

const fetchUsers = async () => {
  if (!datasetData.value?.is_admin) return
  
  usersLoading.value = true
  usersError.value = ''
  
  try {
    const response = await authGet(`/api/dataset/group/${datasetData.value.dataset.group_id}/`)
    userStats.value = response
  } catch (err) {
   
    usersError.value = 'Error'
  } finally {
    usersLoading.value = false
  }
}

const addUser = async () => {
  addingUser.value = true
  try {
    const response = await authPost(`/api/dataset/group/${datasetData.value.dataset.group_id}/`, {
      username: newUser.value.username,
      role_name: newUser.value.role
    })
    

    userStats.value.push(response)

    addUserDialog.value = false
    newUser.value = { username: '', role: 'Viewer' }
    
  } catch (err) {
    
    usersError.value = err.response?.data?.error
  } finally {
    addingUser.value = false
  }
}


const confirmDeleteDialog = ref(false)
const userToDelete = ref(null)

const removeUser = async (user) => {
  userToDelete.value = user
  confirmDeleteDialog.value = true
}

const confirmDelete = async () => {
  if (!userToDelete.value) return
  
  const user = userToDelete.value
  removingUserId.value = user.user_id
  
  try {
    await authDelete(`/api/dataset/group/${datasetData.value.dataset.group_id}/`, {
      user_id: user.user_id 
    })
    

    userStats.value = userStats.value.filter(u => u.user_id !== user.user_id)
    

    confirmDeleteDialog.value = false
    userToDelete.value = null
    
    
  } catch (err) {
   
    usersError.value = err.response?.data?.error 
    

  } finally {
    removingUserId.value = null
  }
}





watch(currentTab, (newTab) => {
  if (newTab === 'metadata' && !metadataData.value) {
    fetchMetadata()
  }
  if (newTab === 'users' && datasetData.value?.is_admin) {
    fetchUsers()
  }
})


const assetHeaders = [
  { title: $t('datasetmanagement.asset_name'), key: 'asset_name' },
  { title: $t('datasetmanagement.records_count'), key: 'records_count', align: 'center' },
  { title: $t('datasetmanagement.segmentation'), key: 'segmentation_count', align: 'center' },
  { title: $t('datasetmanagement.detection'), key: 'detection_count', align: 'center' },
  { title: $t('datasetmanagement.validation_mask_count'), key: 'validation_mask_count', align: 'center'},
  { title: $t('datasetmanagement.validation_bbox_count'), key: 'validation_bbox_count', align: 'center' },
  { title:$t('datasetmanagement.actions'), key: 'actions', align: 'end', sortable: false }
]

const totalRecords = computed(() => {
  if (!datasetData.value?.assets) return 0
  return datasetData.value.assets.reduce((sum, asset) => sum + asset.records_count, 0)
})

const totalSegmentationCount = computed(() => {
  if (!datasetData.value?.assets) return 0
  return datasetData.value.assets.reduce((sum, asset) => sum + asset.segmentation_count, 0)
})

const totalDetectionCount = computed(() => {
  if (!datasetData.value?.assets) return 0
  return datasetData.value.assets.reduce((sum, asset) => sum + asset.detection_count, 0)
})

const totalValidationMaskCount = computed(() => {
  if (!datasetData.value?.assets) return 0
  return datasetData.value.assets.reduce((sum, asset) => sum + asset.validation_mask_count, 0)
})

const totalValidationBboxCount = computed(() => {
  if (!datasetData.value?.assets) return 0
  return datasetData.value.assets.reduce((sum, asset) => sum + asset.validation_bbox_count, 0)
})

const showAssetMetadata = (asset) => {
  selectedAsset.value = asset
  assetMetadataDialog.value = true
}


const fetchDataset = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await authGet(`/api/dataset/management/${props.datasetId}/`)
    if (response.dataset?.metrics) {
      const metricsData = await loadJsonFromUrl(response.dataset.metrics)
      classStats.value = metricsData || []
    } else {
      classStats.value = []
    }
    
    datasetData.value = response
  
  } catch (err) {

    error.value = 'Error'
  } finally {
    loading.value = false
  }
}


const getColorByCount = (count, total = null) => {
  if (count === 0) return 'grey'           
  if (total !== null && total > 0) {
    
    if (count === total) return 'green'    
    if (count < total) return 'orange'     
  }
  

  return 'green'                          
}

const confirmDeleteDatasetDialog = ref(false)
const deleteLoading = ref(false)
const deleteDataset = async () => {
    deleteLoading.value = true
    try {
      await authDelete(`/api/datasets/${props.datasetId}/`)
      confirmDeleteDatasetDialog.value = false
      router.push('/datasets')
    } catch (err) {
      console.error('Error', err)
    }
  
}

onMounted(() => {
  fetchDataset()
  
})


</script>

<style scoped>
.rounded {
  border-radius: 8px;
}

.gap-1 {
  gap: 4px;
}

.json-view {

  padding: 16px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  white-space: pre-wrap;
}
</style>