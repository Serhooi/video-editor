import useLayoutStore from "../store/use-layout-store";
import { Texts } from "./texts";
import { Audios } from "./audios";
import { Elements } from "./elements";
import { Images } from "./images";
import { Videos } from "./videos";
import { Transitions } from "./transitions";
import { AutoSubtitles } from "./auto-subtitles";

const ActiveMenuItem = () => {
  const { activeMenuItem } = useLayoutStore();

  if (activeMenuItem === "texts") {
    return <Texts />;
  }
  if (activeMenuItem === "shapes") {
    return <Elements />;
  }
  if (activeMenuItem === "videos") {
    return <Videos />;
  }

  if (activeMenuItem === "audios") {
    return <Audios />;
  }

  if (activeMenuItem === "images") {
    return <Images />;
  }

  if (activeMenuItem === "transitions") {
    return <Transitions />;
  }

  if (activeMenuItem === "auto-subtitles") {
    return <AutoSubtitles />;
  }

  return null;
};

export const MenuItem = () => {
  return (
    <div className="w-[300px] flex-1">
      <ActiveMenuItem />
    </div>
  );
};

