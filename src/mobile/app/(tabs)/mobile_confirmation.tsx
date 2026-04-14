import { StyleSheet, TouchableOpacity } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useRouter, useLocalSearchParams } from 'expo-router';

export default function ConfirmationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams(); // Retrieve data sent from the context screen

  const handleGoToReview = () => {
    router.push({
      pathname: '/mobile_review',
      params: {
        imageUris: params.imageUris,
        description: params.description,
        priority: params.priority,
        name: params.name,
        contact: params.contact
      }
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Successfully Submitted</Text>
      <View style={styles.separator} lightColor="#eee" darkColor="rgba(255,255,255,0.1)" />
      
      <View style={styles.instructionsContainer}>
        <Text style={styles.instructions}>
          You may be contacted for additional information regarding your report. 
          If you have any further questions, please reach out to example.email@bart.org
        </Text>
      </View>

      <TouchableOpacity style={styles.reviewButton} onPress={handleGoToReview}>
        <Text style={styles.reviewButtonText}>Review Sent Report</Text>
      </TouchableOpacity>
      <TouchableOpacity 
        style={styles.homeButton} 
        onPress={() => router.replace('/mobile_report')}
      >
        <Text style={styles.homeButtonText}>Close</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  separator: {
    marginVertical: 30,
    height: 1,
    width: '80%',
  },
  instructionsContainer: {
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#cccccc',
    padding: 15,
    marginHorizontal: 30,
    borderRadius: 8,
  },
  instructions: {
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  reviewButton: {
    marginTop: 30,
    backgroundColor: '#0099D8', // BART Blue
    paddingVertical: 12,
    paddingHorizontal: 25,
    borderRadius: 5,
    elevation: 2,
  },
  reviewButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
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