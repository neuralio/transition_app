import { redirect } from 'next/navigation';

export default function ChatPage() {
  // Redirect to home page since chat is now the main interface
  redirect('/');
}
