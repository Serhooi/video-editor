import { IAudio } from "@designcombo/types";

export const MUSIC: Partial<IAudio>[] = [
  {
    id: "music1",
    details: { src: "https://www.bensound.com/bensound-music/bensound-ukulele.mp3" },
    type: "audio",
    metadata: {
      fileName: "Ukulele Happy",
      duration: "2:26",
      genre: "Acoustic",
    },
  },
  {
    id: "music2", 
    details: { src: "https://www.bensound.com/bensound-music/bensound-sunny.mp3" },
    type: "audio",
    metadata: {
      fileName: "Sunny",
      duration: "2:20",
      genre: "Pop",
    },
  },
  {
    id: "music3",
    details: { src: "https://www.bensound.com/bensound-music/bensound-creativeminds.mp3" },
    type: "audio", 
    metadata: {
      fileName: "Creative Minds",
      duration: "2:30",
      genre: "Corporate",
    },
  },
  {
    id: "music4",
    details: { src: "https://www.bensound.com/bensound-music/bensound-acousticbreeze.mp3" },
    type: "audio",
    metadata: {
      fileName: "Acoustic Breeze",
      duration: "2:37",
      genre: "Acoustic",
    },
  },
  {
    id: "music5",
    details: { src: "https://www.bensound.com/bensound-music/bensound-energy.mp3" },
    type: "audio",
    metadata: {
      fileName: "Energy",
      duration: "2:59",
      genre: "Electronic",
    },
  },
] as Partial<IAudio>[];

