import {Card, CardContent} from '@/components/ui/card';

interface MessageProps {
  content: string;
  timestamp: string;
  isSender: boolean;
}

const Message: React.FC<MessageProps> = ({content, timestamp, isSender}) => {
  return (
    <div className={`flex ${isSender ? 'justify-end' : 'justify-start'}`}>
      <Card className={`max-w-[70%] ${isSender ? 'bg-primary text-primary-foreground' : 'bg-muted'} m-0`}>
        <CardContent className="px-2 py-0">
          <p>{content}</p>
          <div className={`mt-1 text-${isSender ? 'right' : 'left'} text-xs opacity-70`}>
            {timestamp}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Message;
