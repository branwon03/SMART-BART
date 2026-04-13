import { StyleSheet } from 'react-native';

import { Text, View } from '@/components/Themed';
import { TouchableOpacity, Image } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function TabTwoScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const imageUris = params.imageUris ? JSON.parse(params.imageUris as string) : [];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>mobile context</Text>
      <View style={styles.separator} lightColor="#eee" darkColor="rgba(255,255,255,0.1)" />
      
      {imageUris.length > 0 && (
        <View style={styles.imagesContainer}>
          <View style={styles.photosGrid}>
            {imageUris.map((uri: string, index: number) => (
              <Image key={index} source={{ uri }} style={styles.thumbnail} />
            ))}
          </View>
        </View>
      )}
      
      <View style={styles.navContainer}>
        <TouchableOpacity onPress={() => router.back()} style={styles.navButton}>
          <Ionicons name="arrow-back" size={24} color="black" />
        </TouchableOpacity>
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
    fontSize: 20,
    fontWeight: 'bold',
  },
  separator: {
    marginVertical: 30,
    height: 1,
    width: '80%',
  },
  imagesContainer: {
    marginVertical: 20,
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
