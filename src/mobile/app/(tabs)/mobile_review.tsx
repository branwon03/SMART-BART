import React from 'react';
import { StyleSheet, Image, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { Ionicons } from '@expo/vector-icons';

export default function MobileReviewScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();

  // Parse the images and other details sent from the previous screen
  const imageUris = params.imageUris ? JSON.parse(params.imageUris as string) : [];
  const description = params.description as string || "No description provided.";
  const priority = params.priority as string || "N/A";
  const name = params.name as string || "Anonymous";
  const contact = params.contact as string || "Not provided";

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.header}>Report Summary</Text>

      {/* 1. IMAGE GRID (Up to 3 images) */}
      <View style={styles.imageGrid}>
        {imageUris.slice(0, 3).map((uri: string, index: number) => (
          <Image key={index} source={{ uri }} style={styles.reviewImage} />
        ))}
        {imageUris.length === 0 && (
          <View style={styles.noImagePlaceholder}>
            <Ionicons name="image-outline" size={40} color="#9CA3AF" />
            <Text style={{ color: '#9CA3AF' }}>No images attached</Text>
          </View>
        )}
      </View>

      {/* 2. GREY BOX FOR DESCRIPTION */}
      <View style={styles.detailsContainer}>
        <Text style={styles.label}>Incident Context</Text>
        <View style={styles.greyBox}>
          <Text style={styles.descriptionText}>{description}</Text>
        </View>

        {/* METADATA ROWS */}
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Priority:</Text>
          <Text style={[styles.metaValue, { color: priority === 'high' ? 'red' : 'black' }]}>
            {priority.toUpperCase()}
          </Text>
        </View>

        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Submitted By:</Text>
          <Text style={styles.metaValue}>{name}</Text>
        </View>

        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Contact Info:</Text>
          <Text style={styles.metaValue}>{contact}</Text>
        </View>
      </View>

      
      <TouchableOpacity 
        style={styles.homeButton} 
        onPress={() => router.replace('/mobile_report')}
      >
        <Text style={styles.homeButtonText}>Close</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    padding: 20,
    alignItems: 'center',
  },
  header: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  imageGrid: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
    marginBottom: 25,
  },
  reviewImage: {
    width: 100,
    height: 100,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D1D5DB',
  },
  noImagePlaceholder: {
    width: 300,
    height: 100,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    borderStyle: 'dashed',
    borderWidth: 1,
    borderColor: '#9CA3AF',
  },
  detailsContainer: {
    width: '100%',
    paddingHorizontal: 10,
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#374151',
  },
  greyBox: {
    backgroundColor: '#D1D5DB', // Matching your web app grey
    padding: 15,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: '#9CA3AF',
    marginBottom: 20,
  },
  descriptionText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#1F2937',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  metaLabel: {
    fontWeight: '600',
    color: '#4B5563',
  },
  metaValue: {
    color: '#111827',
  },
  homeButton: {
    marginTop: 40,
    backgroundColor: '#0099D8',
    paddingVertical: 12,
    paddingHorizontal: 40,
    borderRadius: 5,
  },
  homeButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
});