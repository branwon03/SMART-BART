import { StyleSheet } from 'react-native';

import { Text, View } from '@/components/Themed';
import { TouchableOpacity, Image, TextInput, TouchableWithoutFeedback, Keyboard, Modal, FlatList } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';

export default function TabTwoScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const imageUris = params.imageUris ? JSON.parse(params.imageUris as string) : [];
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [showPriorityDropdown, setShowPriorityDropdown] = useState(false);
  
  const priorityOptions = [
    { label: 'Low', value: 'low' },
    { label: 'Medium', value: 'medium' },
    { label: 'High', value: 'high' },
    { label: 'Critical', value: 'critical' },
    { label : 'Not sure', value: 'Not sure'}
  ];

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View style={styles.container}>
        <Text style={styles.title}>mobile context</Text>
        
        {imageUris.length > 0 && (
          <View style={styles.imagesContainer}>
            <View style={styles.photosGrid}>
              {imageUris.map((uri: string, index: number) => (
                <Image key={index} source={{ uri }} style={styles.thumbnail} />
              ))}
            </View>
          </View>
        )}
        
        <View style={styles.descriptionSection}>
          <Text style={styles.label}>Description of Issue</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Describe the issue..."
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={4}
          />
        </View>
        
        <View style={styles.prioritySection}>
          <Text style={styles.label}>Priority Level</Text>
          <TouchableOpacity 
            style={styles.priorityButton}
            onPress={() => setShowPriorityDropdown(true)}
          >
            <Text style={styles.priorityButtonText}>
              {priorityOptions.find(opt => opt.value === priority)?.label}
            </Text>
            <Ionicons name="chevron-down" size={20} color="black" />
          </TouchableOpacity>
          
          <Modal
            visible={showPriorityDropdown}
            transparent
            
            onRequestClose={() => setShowPriorityDropdown(false)}
          >
            <TouchableWithoutFeedback onPress={() => setShowPriorityDropdown(false)}>
              <View style={styles.modalOverlay}>
                <View style={styles.dropdownMenu}>
                  <FlatList
                    data={priorityOptions}
                    keyExtractor={(item) => item.value}
                    renderItem={({ item }) => (
                      <TouchableOpacity
                        style={[
                          styles.dropdownItem,
                          priority === item.value && styles.dropdownItemSelected,
                        ]}
                        onPress={() => {
                          setPriority(item.value);
                          setShowPriorityDropdown(false);
                        }}
                      >
                        <Text
                          style={[
                            styles.dropdownItemText,
                            priority === item.value && styles.dropdownItemTextSelected,
                          ]}
                        >
                          {item.label}
                        </Text>
                      </TouchableOpacity>
                    )}
                  />
                </View>
              </View>
            </TouchableWithoutFeedback>
          </Modal>
        </View>
        
        <View style={styles.navContainer}>
          <TouchableOpacity onPress={() => router.back()} style={styles.navButton}>
            <Ionicons name="arrow-back" size={24} color="black" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableWithoutFeedback>
    
  );
}







const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 80,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
  },
  imagesContainer: {
    marginVertical: 10,
  },
  photosGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  thumbnail: {
    width: 80,
    height: 80,
    margin: 5,
    borderRadius: 5,
  },
  descriptionSection: {
    marginTop: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#cccccc',
    borderRadius: 5,
    padding: 10,
    fontSize: 14,
    minHeight: 100,
  },
  prioritySection: {
    marginTop: 20,
    marginBottom: 20,
  },
  priorityButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#cccccc',
    borderRadius: 5,
    paddingHorizontal: 10,
    paddingVertical: 12,
  },
  priorityButtonText: {
    fontSize: 14,
    color: 'black',
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  dropdownMenu: {
    backgroundColor: 'white',
    borderRadius: 8,
    width: '80%',
    maxHeight: 200,
    overflow: 'hidden',
  },
  dropdownItem: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  dropdownItemSelected: {
    backgroundColor: '#007bff',
  },
  dropdownItemText: {
    fontSize: 14,
    color: 'black',
  },
  dropdownItemTextSelected: {
    color: 'white',
  },
  navContainer: {
    position: 'absolute',
    bottom: 20,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  navButton: {
    padding: 10,
  },
});
