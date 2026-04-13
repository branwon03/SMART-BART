import { StyleSheet } from 'react-native';
import { submitMobileReport } from '../../lib/submissions';
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
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const priorityOptions = [
    { label: 'Low', value: 'low' },
    { label: 'Medium', value: 'medium' },
    { label: 'High', value: 'high' },
    { label: 'Critical', value: 'critical' },
    { label : 'Not sure', value: 'Not sure'}
  ];

  const handleSubmit = async () => {
  // 1. Basic Validation (Mirroring your web app logic)
  if (!description.trim() || !name.trim() || !contact.trim()) {
    alert("Please fill out all fields before submitting.");
    return;
  }

  setIsSubmitting(true);

  try {
    // 2. The API Call
    // Note: We combine name/contact combined into description for now
    await submitMobileReport({
      images: imageUris,
      description: `Report by: ${name}\nContact: ${contact}\n\nNotes: ${description}`,
      location: "MOBILE_UPLOAD", // You can update this to a specific station ID later
    });

    // 3. Success! Move to confirmation
    router.push('/mobile_confirmation');
  } catch (error) {
    console.error("Submission Error:", error);
    alert("Could not reach the server. Make sure your FastAPI backend is running at " + process.env.EXPO_PUBLIC_API_BASE_URL);
  } finally {
    setIsSubmitting(false);
  }
};

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View style={styles.container}>
        
        
        {imageUris.length > 0 && (
          <View style={styles.imagesContainer}>
            <View style={styles.photosGrid}>
              {imageUris.slice(0, 3).map((uri: string, index: number) => (
                <Image key={index} source={{ uri }} style={styles.thumbnail} />
              ))}
              {imageUris.length > 4 && (
                <View style={styles.morePhotosIndicator}>
                  <Text style={styles.morePhotosText}>+{imageUris.length - 3}</Text>
                </View>
              )}
            </View>
          </View>
        )}
        
        <Text style={styles.locationText}>Exact Location will be determined by image metadata</Text>
        
        <View style={styles.descriptionSection}>
          <Text style={styles.label}>Description of Issue</Text>
          <TextInput
            style={styles.descriptionInput}
            placeholder="Describe the issue..."
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={2}
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

          <View style={styles.contactSection}>
          <Text style={styles.label}>Name</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Enter your name..."
            value={name}
            onChangeText={setName}
          />
          
          <Text style={styles.label}>Email or Phone Number</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Enter email or phone..."
            value={contact}
            onChangeText={setContact}
            keyboardType="email-address"
          />
        </View>
          
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
        
        <Text style={styles.emergencyText}>In case of emergency, call 911</Text>
        
        <TouchableOpacity 
          style={[styles.submitButton, isSubmitting && { opacity: 0.6 }]} 
          onPress={handleSubmit}
          disabled={isSubmitting}
        >
          <Text style={styles.submitButtonText}>
            isSubmitting ? "Submitting..." : "Submit Report"}
          </Text>
        </TouchableOpacity>
        
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
  morePhotosIndicator: {
    width: 80,
    height: 80,
    margin: 5,
    borderRadius: 5,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  morePhotosText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  locationText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 10,
    marginBottom: 10,
    fontStyle: 'italic',
  },
  descriptionSection: {
    marginTop: 20,
  },
  contactSection: {
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
    minHeight: 40,
    marginBottom: 0,
  },
  descriptionInput: {
    borderWidth: 1,
    borderColor: '#cccccc',
    borderRadius: 5,
    padding: 10,
    fontSize: 14,
    minHeight: 65,
    marginBottom: 15,
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
  emergencyText: {
    fontSize: 17,
    color: '#ff4444',
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 0,
    marginBottom: 2,
  },
  submitButton: {
    backgroundColor: '#007bff',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
    marginBottom: 2,
    alignSelf: 'center',
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },  navContainer: {
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
