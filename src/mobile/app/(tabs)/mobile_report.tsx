import { StyleSheet } from 'react-native';

import { Text, View } from '@/components/Themed';
import { useState } from 'react';
import { TouchableOpacity, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

export default function TabTwoScreen() {
  const [images, setImages] = useState([]);

  const pickImage = async () => {
    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (permissionResult.granted === false) {
      alert('Permission to access camera roll is required!');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      quality: 1,
    });
    if (!result.canceled) {
      setImages(result.assets);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Incident Reporting Form</Text>
      <View style={styles.instructionsContainer}>
        <Text style={styles.instructions}>Please upload one or more images of the identified incident. 
          You will be prompted to enter your name, contact information, and additional context on the next page.</Text>
      </View>
      <View style={styles.uploadContainer}>
        <TouchableOpacity onPress={pickImage} style={styles.uploadButton}>
          <Text style={styles.uploadButtonText}>Upload Images</Text>
        </TouchableOpacity>
        {images.map((image, index) => (
          <Image key={index} source={{ uri: image.uri }} style={styles.image} />
        ))}
      </View>

    </View>
  );
}







const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: 20,
  },
  title: {
    fontSize: 30,
    fontWeight: 'bold',
    
  },
  instructionsContainer: {
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#cccccc',
    padding: 10,
    marginHorizontal: 20,
    marginTop: 10,
  },
  instructions: {
    fontSize: 10,
    textAlign: 'center',
    
  },
  uploadContainer: {
    marginTop: 20,
    alignItems: 'center',
  },
  uploadButton: {
    backgroundColor: '#007bff',
    padding: 10,
    borderRadius: 5,
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 16,
  },
  image: {
    width: 100,
    height: 100,
    margin: 5,
  },
});
